
from typing import List, Dict, Any, Union,Optional
from enum import Enum
from dataclasses import dataclass, field
from rag.message.MessageRole import MessageRole
 
@dataclass
class ChatMessage:
    """
    Represents a single message in a chat conversation.
    
    Attributes:
        role: Role of the message sender
        content: Message content text
        name: Optional name for the message sender
        function_call: Optional function call data
    """
    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate message after initialization."""
        if not self.content and not self.function_call:
            raise ValueError("Message must have either content or function_call")
        
        # Ensure role is MessageRole enum
        if isinstance(self.role, str):
            self.role = MessageRole(self.role)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert message to dictionary format for API calls.
        
        Returns:
            Dictionary representation of message
        """
        result = {
            "role": self.role.value,
            "content": self.content
        }
        
        if self.name:
            result["name"] = self.name
        
        if self.function_call:
            result["function_call"] = self.function_call
        
        return result
