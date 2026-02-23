
from typing import Dict, Any, Optional, Protocol,List


class LLMProtocol(Protocol):
    """Protocol defining the interface for LLM implementations."""
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        ...
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response from chat messages."""
        ...

