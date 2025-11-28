from typing import List, Dict
import uuid

class ConversationMemory:
    """Manages short-term conversation history"""
    
    def __init__(self, max_turns: int = 5):
        self.conversation_history: List[Dict[str, str]] = []
        self.max_memory_turns = max_turns

    def add(self, user_message: str, assistant_response: str):
        """Add user and assistant messages to history"""
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # Keep only recent history
        if len(self.conversation_history) > self.max_memory_turns * 2:
            self.conversation_history = self.conversation_history[-(self.max_memory_turns * 2):]

    def get_context(self) -> str:
        """Format conversation history for prompts"""
        if not self.conversation_history:
            return "No previous conversation history."
        
        memory_text = "Recent conversation history:\n"
        for msg in self.conversation_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            memory_text += f"{role}: {msg['content']}\n"
        
        return memory_text

    def clear(self):
        """Clear all history"""
        self.conversation_history = []

    def get_history(self) -> List[Dict[str, str]]:
        """Get raw history"""
        return self.conversation_history
    

