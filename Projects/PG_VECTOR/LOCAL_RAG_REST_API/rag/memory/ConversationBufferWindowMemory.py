"""
Window memory that keeps only recent conversation turns.
Memory-efficient for long conversations.
"""


from rag.memory.BaseMemory import BaseMemory
from typing import Optional,Dict,Any
from rag.exception import MemoryException
from rag.memory import ConversationTurn
from rag.chain import LLMProtocol
import logging
import threading
logger = logging.getLogger(__name__)


class ConversationBufferWindowMemory(BaseMemory):
    """
    Production-ready sliding window memory implementation.
    
    Keeps only the most recent N conversation turns.
    
    Features:
    - Fixed memory footprint
    - Automatic old message pruning
    - Thread-safe operations
    
    Suitable for:
    - Long-running conversations
    - Memory-constrained environments
    - Applications needing recent context only
    
    Attributes:
        chat_history: Deque of recent conversation turns
        k: Number of recent turns to keep
    """
    
    def __init__(self,
                 memory_key: str = "history",
                 input_key: str = "input",
                 output_key: str = "output",
                 k: int = 5,
                 return_messages: bool = False):
        """
        Initialize window memory.
        
        Args:
            memory_key: Key for memory in context
            input_key: Key for user input
            output_key: Key for AI output
            k: Number of recent conversation pairs to keep
            return_messages: Return structured messages vs formatted string
            
        Raises:
            ValueError: If k is invalid
        """
        super().__init__(memory_key, input_key, output_key)
        
        if k < 1:
            raise ValueError("Window size k must be at least 1")
        
        from collections import deque
        
        self.k = k
        self.return_messages = return_messages
        # Use deque for efficient FIFO operations
        self.chat_history: deque = deque(maxlen=k)
        self._lock = threading.Lock()
        
        logger.info(f"ConversationBufferWindowMemory initialized: k={k}")
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        Save conversation turn to window.
        
        Automatically removes oldest turn if window is full.
        
        Args:
            inputs: User input dictionary
            outputs: AI output dictionary
            
        Raises:
            MemoryException: If save fails
        """
        try:
            user_message = self._extract_input(inputs)
            ai_message = self._extract_output(outputs)
            
            turn = ConversationTurn(
                user_message=user_message,
                ai_message=ai_message
            )
            
            with self._lock:
                # Deque automatically removes oldest when full
                self.chat_history.append(turn)
            
            logger.debug(f"Saved turn to window (size: {len(self.chat_history)}/{self.k})")
            
        except ValueError as ve:
            logger.error(f"Failed to save context: {str(ve)}")
            raise MemoryException(f"Save failed: {str(ve)}")
        except Exception as e:
            logger.error(f"Unexpected error saving context: {str(e)}")
            raise MemoryException(f"Save error: {str(e)}")
    
    def load_memory_variables(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Load recent conversation history from window.
        
        Args:
            inputs: Optional input context (not used)
            
        Returns:
            Dictionary with recent conversation history
        """
        try:
            with self._lock:
                if not self.chat_history:
                    return {self.memory_key: "" if not self.return_messages else []}
                
                if self.return_messages:
                    messages = []
                    for turn in self.chat_history:
                        messages.append({"role": "user", "content": turn.user_message})
                        messages.append({"role": "assistant", "content": turn.ai_message})
                    return {self.memory_key: messages}
                else:
                    formatted = self._format_history()
                    return {self.memory_key: formatted}
                    
        except Exception as e:
            logger.error(f"Failed to load memory: {str(e)}")
            raise MemoryException(f"Load error: {str(e)}")
    
    def _format_history(self) -> str:
        """Format recent chat history as string."""
        formatted_parts = []
        
        for turn in self.chat_history:
            formatted_parts.append(f"User: {turn.user_message}")
            formatted_parts.append(f"Assistant: {turn.ai_message}")
        
        return "\n".join(formatted_parts)
    
    def clear(self) -> None:
        """Clear all conversation history."""
        with self._lock:
            self.chat_history.clear()
        logger.info("Cleared window memory")
    
    def get_window_size(self) -> int:
        """Get configured window size."""
        return self.k
    
    def get_current_size(self) -> int:
        """Get current number of turns in window."""
        with self._lock:
            return len(self.chat_history)


# Example usage:
# # Keep only last 3 conversation pairs
# memory = ConversationBufferWindowMemory(k=3)
# 
# # After 5 conversations, only last 3 are kept
# for i in range(5):
#     memory.save_context(
#         inputs={"input": f"Message {i}"},
#         outputs={"output": f"Response {i}"}
#     )
# 
# history = memory.load_memory_variables()
# # Only contains: Message 2, Response 2, Message 3, Response 3, Message 4, Response 4