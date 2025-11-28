from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
import os

@dataclass
class Config:
    neo4j_uri: str = field(default_factory=lambda: os.environ.get("NEO4J_URI", "bolt://127.0.0.1:7687"))
    neo4j_user: str = field(default_factory=lambda: os.environ.get("NEO4J_USERNAME", "neo4j"))
    neo4j_password: str = field(default_factory=lambda: os.environ.get("NEO4J_PASSWORD", "MyPassword"))
    embedding_model_name: str = "all-MiniLM-L6-v2" # sentence-transformers small-but-good
    chunk_size: int = 500
    chunk_overlap: int = 50
    openai_model: str = "gpt-4o-mini" # put your preferred completion model
    openai_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", "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"))