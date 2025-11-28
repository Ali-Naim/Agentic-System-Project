from sentence_transformers import SentenceTransformer
from .neo4j_connector import Neo4jConnector
from config import Config
import numpy as np
import json
import os
from typing import List, Optional, Tuple, Dict, Any
import openai
import uuid




class GraphMemory:
    """High-level API for storing documents and chunks in Neo4j."""


    def __init__(self, connector: Neo4jConnector, cfg: Config):
        self.conn = connector
        self.cfg = cfg
        self.embedder = SentenceTransformer(cfg.embedding_model_name)


    # create minimal constraints / indexes
        self._init_schema()


    def _init_schema(self):
        # create uniqueness constraint for Document.id and index for Chunk.id
        q = """
        CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;
        CREATE INDEX IF NOT EXISTS FOR (c:Chunk) ON (c.chunk_id);
        """
        try:
            self.conn.run(q)
        except Exception:
            pass

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        if np.all(a == 0) or np.all(b == 0):
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    
    def _chunk_text(self, text: str) -> List[str]:
        max_len = self.cfg.chunk_size
        overlap = self.cfg.chunk_overlap
        tokens = text.split()
        chunks = []
        i = 0
        while i < len(tokens):
            chunk_tokens = tokens[i : i + max_len]
            chunks.append(" ".join(chunk_tokens))
            i += max_len - overlap
        return chunks
    
    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        arr = self.embedder.encode(texts, show_progress_bar=False)
        # ensure python lists
        return [list(map(float, x)) for x in np.array(arr)]
    
    def add_document(self, doc_id: str, title: str, text: str, metadata: dict = None) -> None:
        """Add a document + chunks + embeddings to the graph.


        Node layout:
        (d:Document {doc_id, title, metadata_json})
        (c:Chunk {chunk_id, text, embedding, position})
        (d)-[:HAS_CHUNK]->(c)
        """
        metadata = metadata or {}
        chunks = self._chunk_text(text)
        embeddings = self._embed_texts(chunks)


        # create document node
        self.conn.run(
            "MERGE (d:Document {doc_id: $doc_id}) SET d.title = $title, d.metadata_json = $metadata_json",
                {
                    "doc_id": doc_id,
                    "title": title,
                    "metadata_json": json.dumps(metadata),
                },
        )


        # create chunk nodes and relationships
        for idx, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{doc_id}::chunk::{idx}"
            self.conn.run(
                "MERGE (c:Chunk {chunk_id: $chunk_id})\n"
                "SET c.text = $text, c.embedding = $embedding, c.position = $position\n"
                "WITH c\n"
                "MATCH (d:Document {doc_id: $doc_id})\n"
                "MERGE (d)-[:HAS_CHUNK {pos: $position}]->(c)",
                {
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "embedding": emb,
                    "position": idx,
                    "doc_id": doc_id,
                },
            )


    def _fetch_all_chunk_embeddings(self, limit: Optional[int] = None) -> List[Tuple[str, List[float], str, dict, str]]:
        """
        Return list of tuples (chunk_id, embedding, text, metadata, doc_title)
        """
        q = """
            MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
            RETURN c.chunk_id AS chunk_id,
                c.embedding AS embedding,
                c.text AS text,
                d.metadata_json AS metadata_json,
                d.title AS doc_title
        """
        if limit:
            q += f" LIMIT {int(limit)}"

        records = self.conn.run(q)
        out = []
        for rec in records:
            embedding = rec.get("embedding") or rec.get("c.embedding")
            if embedding is None:
                continue
            chunk_id = rec.get("chunk_id")
            text = rec.get("text")
            meta = json.loads(rec.get("metadata_json") or "{}")
            doc_title = rec.get("doc_title")
            out.append((chunk_id, embedding, text, meta, doc_title))
        return out

    
    def retrieve(self, query: str, top_k: int = 2, candidate_limit: Optional[int] = None) -> List[Dict[str, Any]]:
        q_emb = np.array(self.embedder.encode([query])[0])
        rows = self._fetch_all_chunk_embeddings(limit=candidate_limit)

        sims = []
        for chunk_id, emb_list, text, meta, doc_title in rows:
            emb = np.array(emb_list)
            score = float(self.cosine_similarity(q_emb, emb))
            sims.append({
                "chunk_id": chunk_id,
                "score": score,
                "text": text,
                "chapter": meta.get("chapter") if meta else None,
                "course": meta.get("course") if meta else None,
                "doc_title": doc_title
            })

        sims.sort(key=lambda x: x["score"], reverse=True)
        return sims[:top_k]

    
    def answer_question(self, question: str, top_k: int = 1, use_openai: bool = True):
        """
        Retrieve context + call an LLM to synthesize an answer using the modern OpenAI API format.

        If OpenAI is unavailable (no key, disabled, or error), return retrieved context only.
        """

        # Step 1: Retrieve the best-matching chunks
        hits = self.retrieve(question, top_k=top_k)


        # Build readable context text
        context_text = "\n".join(
            [f"[Document: {h.get('doc_title')}] (score={h['score']:.4f})" for h in hits]
        )


        
        

        # Step 2: Construct the prompt
        prompt = f"""
        You are an assistant answering a question using ONLY the retrieved sources listed below.

        DO NOT include the chunk text in your answer.
        Answer in maximum 3 sentences.
        Provide a short, concise answer.
        At the end, provide a field: "sources": [list of document names].

        Retrieved Sources:
        {context_text}

        Question: {question}

        Return output ONLY in this JSON format:
        {{
        "answer": "<short answer>",
        "sources": ["document_name_1.pdf", "document_name_2.pdf"]
        }}
        """

                        
        # Step 3: Use OpenAI (new API format)
        if use_openai and (self.cfg.openai_api_key or os.environ.get("OPENAI_API_KEY")):
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.cfg.openai_api_key or os.environ.get("OPENAI_API_KEY"))

                response = client.chat.completions.create(
                    model=self.cfg.openai_model or "gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )

                raw = response.choices[0].message.content.strip()

                # Ensure valid JSON
                try:
                    parsed = json.loads(raw)
                    print(parsed)
                except:
                    # fallback: wrap into JSON if not valid
                    parsed = {"answer": raw, "sources": [h.get("doc_title") for h in hits]}

                return {
                    "message": f"{parsed.get('answer')} {parsed.get('sources') or [h['doc_title'] for h in hits]}"
                }


            except Exception as e:
                return {
                    "error": str(e),
                    "context_hits": hits
                }

        # Step 4: Fallback — no OpenAI, return context only
        return {
            "answer": None,
            "context_hits": hits
        }



    def addGraphFile(self, doc_text: str, title: str = None, metadata: dict = None):
        """
        Accepts raw text (extracted from PDF or plain text) and loads into Neo4j.
        """
        doc_id = str(uuid.uuid4())
        title = title or f"Uploaded-{doc_id[:8]}"
        print(title)
        self.add_document(
            doc_id=doc_id,
            title=title,
            text=doc_text,
            metadata=metadata or {}
        )

        return {"doc_id": doc_id, "title": title}