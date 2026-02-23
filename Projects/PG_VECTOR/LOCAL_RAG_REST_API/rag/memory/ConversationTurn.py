"""
Buffer memory that stores entire conversation history.
Simple but memory-intensive for long conversations.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from rag.memory import BaseMemory
import threading


@dataclass
class ConversationTurn:
    """
    Represents a single conversation turn.
    
    Attributes:
        user_message: User input
        ai_message: AI response
        timestamp: When this turn occurred
        metadata: Additional metadata
    """
    user_message: str
    ai_message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "user": self.user_message,
            "assistant": self.ai_message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class ConversationBufferMemory(BaseMemory):
    """
    Production-ready buffer memory implementation.
    
    Stores complete conversation history in memory.
    
    Features:
    - Thread-safe operations
    - Timestamp tracking
    - Metadata support
    - Export/import functionality
    
    Suitable for:
    - Short to medium conversations
    - Development and testing
    - Applications where full history is needed
    
    Attributes:
        chat_history: List of conversation turns
        max_turns: Maximum turns to store (None = unlimited)
        return_messages: Return as message objects vs string
    """
    
    def __init__(self,
                 memory_key: str = "history",
                 input_key: str = "input",
                 output_key: str = "output",
                 max_turns: Optional[int] = None,
                 return_messages: bool = False):
        """
        Initialize conversation buffer memory.
        
        Args:
            memory_key: Key for memory in context
            input_key: Key for user input
            output_key: Key for AI output
            max_turns: Maximum conversation turns to store
            return_messages: Return structured messages vs formatted string
            
        Raises:
            ValueError: If max_turns is invalid
        """
        super().__init__(memory_key, input_key, output_key)
        
        if max_turns is not None and max_turns < 1:
            raise ValueError("max_turns must be at least 1")
        
        self.chat_history: List[ConversationTurn] = []
        self.max_turns = max_turns
        self.return_messages = return_messages
        
        # Thread lock for concurrent access
        self._lock = threading.Lock()
        
        logger.info(
            f"ConversationBufferMemory initialized: max_turns={max_turns}, "
            f"return_messages={return_messages}"
        )
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        Save conversation turn to buffer.
        
        Args:
            inputs: User input dictionary
            outputs: AI output dictionary
            
        Raises:
            MemoryException: If save fails
        """
        try:
            # Extract messages
            user_message = self._extract_input(inputs)
            ai_message = self._extract_output(outputs)
            
            # Create conversation turn
            turn = ConversationTurn(
                user_message=user_message,
                ai_message=ai_message,
                metadata={
                    'input_tokens': len(user_message.split()),
                    'output_tokens': len(ai_message.split())
                }
            )
            
            # Thread-safe append
            with self._lock:
                self.chat_history.append(turn)
                
                # Enforce max_turns limit
                if self.max_turns and len(self.chat_history) > self.max_turns:
                    # Remove oldest turns
                    self.chat_history = self.chat_history[-self.max_turns:]
                    logger.debug(f"Trimmed history to {self.max_turns} turns")
            
            logger.debug(f"Saved turn to memory (total: {len(self.chat_history)})")
            
        except ValueError as ve:
            logger.error(f"Failed to save context: {str(ve)}")
            raise MemoryException(f"Save failed: {str(ve)}")
        except Exception as e:
            logger.error(f"Unexpected error saving context: {str(e)}")
            raise MemoryException(f"Save error: {str(e)}")
    
    def load_memory_variables(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Load conversation history from buffer.
        
        Args:
            inputs: Optional input context (not used in buffer memory)
            
        Returns:
            Dictionary with formatted conversation history
        """
        try:
            with self._lock:
                if not self.chat_history:
                    return {self.memory_key: "" if not self.return_messages else []}
                
                if self.return_messages:
                    # Return as structured message list
                    messages = []
                    for turn in self.chat_history:
                        messages.append({"role": "user", "content": turn.user_message})
                        messages.append({"role": "assistant", "content": turn.ai_message})
                    return {self.memory_key: messages}
                else:
                    # Return as formatted string
                    formatted = self._format_history()
                    return {self.memory_key: formatted}
                    
        except Exception as e:
            logger.error(f"Failed to load memory: {str(e)}")
            raise MemoryException(f"Load error: {str(e)}")
    
    def _format_history(self) -> str:
        """
        Format chat history as readable string.
        
        Returns:
            Formatted conversation history
        """
        formatted_parts = []
        
        for turn in self.chat_history:
            formatted_parts.append(f"User: {turn.user_message}")
            formatted_parts.append(f"Assistant: {turn.ai_message}")
        
        return "\n".join(formatted_parts)
    
    def clear(self) -> None:
        """Clear all conversation history."""
        with self._lock:
            self.chat_history.clear()
        logger.info("Cleared conversation buffer memory")
    
    def get_turn_count(self) -> int:
        """
        Get number of conversation turns stored.
        
        Returns:
            Number of turns
        """
        with self._lock:
            return len(self.chat_history)
    
    def export_history(self) -> List[Dict[str, Any]]:
        """
        Export conversation history as JSON-serializable list.
        
        Returns:
            List of conversation turn dictionaries
        """
        with self._lock:
            return [turn.to_dict() for turn in self.chat_history]
    
    def import_history(self, history: List[Dict[str, Any]]) -> None:
        """
        Import conversation history from exported format.
        
        Args:
            history: List of turn dictionaries
            
        Raises:
            ValueError: If history format is invalid
        """
        try:
            imported_turns = []
            
            for turn_dict in history:
                # Validate required fields
                if 'user' not in turn_dict or 'assistant' not in turn_dict:
                    raise ValueError("Turn must have 'user' and 'assistant' fields")
                
                # Parse timestamp if present
                timestamp = datetime.utcnow()
                if 'timestamp' in turn_dict:
                    try:
                        timestamp = datetime.fromisoformat(turn_dict['timestamp'])
                    except:
                        logger.warning("Invalid timestamp, using current time")
                
                # Create turn
                turn = ConversationTurn(
                    user_message=turn_dict['user'],
                    ai_message=turn_dict['assistant'],
                    timestamp=timestamp,
                    metadata=turn_dict.get('metadata', {})
                )
                imported_turns.append(turn)
            
            # Replace history
            with self._lock:
                self.chat_history = imported_turns
            
            logger.info(f"Imported {len(imported_turns)} conversation turns")
            
        except Exception as e:
            logger.error(f"Failed to import history: {str(e)}")
            raise ValueError(f"Import failed: {str(e)}")


# Example usage:
# memory = ConversationBufferMemory(max_turns=10)
# 
# # Save conversation
# memory.save_context(
#     inputs={"input": "Hello!"},
#     outputs={"output": "Hi! How can I help you?"}
# )
# 
# # Load history
# history = memory.load_memory_variables()
# print(history["history"])
# # Output:
# # User: Hello!
# # Assistant: Hi! How can I help you?