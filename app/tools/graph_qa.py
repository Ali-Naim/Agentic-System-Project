class GraphQATool:
    def __init__(self, graph_memory):
        self.graph_memory = graph_memory

    def answer_q(self, question: str):
        """
        Query Neo4j graph memory to answer the question.
        """
        # Use LLM to summarize / answer
        return self.graph_memory.answer_question(question)
            

    