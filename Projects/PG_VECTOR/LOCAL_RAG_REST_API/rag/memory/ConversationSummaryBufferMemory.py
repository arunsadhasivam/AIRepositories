"""
Hybrid memory combining summary and buffer approaches.
Best of both worlds for production use.
"""

import logging
from rag.memory.BaseMemory import BaseMemory
from typing import Optional,Dict,Any
from rag.exception import MemoryException
from rag.memory import ConversationTurn
from rag.chain import LLMProtocol
logger = logging.getLogger(__name__)


class ConversationSummaryBufferMemory(BaseMemory):
    """
    Production-ready hybrid summary + buffer memory.
    
    Maintains summary of old conversations + buffer of recent ones.
    
    Features:
    - Fixed buffer size for recent messages
    - Automatic summarization of overflow
    - Token-aware compression
    
    Suitable for:
    - Production chatbots
    - Long conversations with token limits
    - Applications needing both detail and history
    
    Attributes:
        llm: Language model for summarization
        chat_history: Recent conversation buffer
        summary: Summary of older conversations
        buffer_size: Number of recent turns to keep
    """
    
    def __init__(self,
                 llm: LLMProtocol,
                 memory_key: str = "history",
                 input_key: str = "input",
                 output_key: str = "output",
                 max_token_limit: int = 2000,
                 buffer_size: int = 3):
        """
        Initialize hybrid memory.
        
        Args:
            llm: Language model for summarization
            memory_key: Key for memory in context
            input_key: Key for user input
            output_key: Key for AI output
            max_token_limit: Total token limit
            buffer_size: Number of recent turns to keep verbatim
            
        Raises:
            ValueError: If parameters are invalid
        """
        super().__init__(memory_key, input_key, output_key)
        
        if llm is None:
            raise ValueError("LLM cannot be None")
        if buffer_size < 1:
            raise ValueError("buffer_size must be at least 1")
        
        self.llm = llm
        self.max_token_limit = max_token_limit
        self.buffer_size = buffer_size
        
        from collections import deque
        self.chat_history: deque = deque(maxlen=buffer_size)
        self.summary: str = ""
        self._lock = threading.Lock()
        
        logger.info(
            f"ConversationSummaryBufferMemory initialized: "
            f"buffer_size={buffer_size}, max_tokens={max_token_limit}"
        )
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        Save conversation turn to buffer.
        
        When buffer overflows, oldest turn is moved to summary.
        
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
                # Check if buffer will overflow
                if len(self.chat_history) == self.buffer_size:
                    # Move oldest turn to summary before adding new one
                    oldest_turn = self.chat_history[0]
                    self._add_to_summary(oldest_turn)
                
                # Add new turn (deque automatically handles overflow)
                self.chat_history.append(turn)
                
                # Check token limit and compress if needed
                if self._estimate_tokens() > self.max_token_limit:
                    self._compress_summary()
            
            logger.debug(f"Saved turn to memory (buffer: {len(self.chat_history)}/{self.buffer_size})")
            
        except ValueError as ve:
            logger.error(f"Failed to save context: {str(ve)}")
            raise MemoryException(f"Save failed: {str(ve)}")
        except Exception as e:
            logger.error(f"Unexpected error saving context: {str(e)}")
            raise MemoryException(f"Save error: {str(e)}")
    
    def _add_to_summary(self, turn: ConversationTurn) -> None:
        """
        Add a conversation turn to the summary.
        
        Args:
            turn: Conversation turn to add
        """
        try:
            turn_text = f"User: {turn.user_message}\nAssistant: {turn.ai_message}"
            
            if not self.summary:
                # First turn - just use it as summary
                self.summary = turn_text
            else:
                # Append to existing summary with LLM
                prompt = f"""Add this new conversation turn to the existing summary:

Existing summary:
{self.summary}

New turn:
{turn_text}

Updated summary (keep it concise):"""
                
                self.summary = self.llm.generate(prompt)
            
            logger.debug("Added turn to summary")
            
        except Exception as e:
            logger.error(f"Failed to add to summary: {str(e)}")
            # Fallback: just append the text
            self.summary += f"\n{turn_text}"
    
    def _compress_summary(self) -> None:
        """Compress summary if it's getting too long."""
        if not self.summary:
            return
        
        try:
            prompt = f"""Compress this conversation summary to be more concise while preserving key information:

{self.summary}

Compressed summary:"""
            
            compressed = self.llm.generate(prompt)
            self.summary = compressed
            
            logger.info("Compressed summary")
            
        except Exception as e:
            logger.error(f"Failed to compress summary: {str(e)}")
    
    def _estimate_tokens(self) -> int:
        """Estimate total token count."""
        summary_chars = len(self.summary)
        history_chars = sum(
            len(turn.user_message) + len(turn.ai_message)
            for turn in self.chat_history
        )
        return (summary_chars + history_chars) // 4
    
    def load_memory_variables(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Load summary and buffer.
        
        Args:
            inputs: Optional input context (not used)
            
        Returns:
            Dictionary with summary and recent messages
        """
        try:
            with self._lock:
                parts = []
                
                # Add summary if exists
                if self.summary:
                    parts.append(f"Earlier conversation summary:\n{self.summary}")
                
                # Add recent buffer
                if self.chat_history:
                    recent_parts = []
                    for turn in self.chat_history:
                        recent_parts.append(f"User: {turn.user_message}")
                        recent_parts.append(f"Assistant: {turn.ai_message}")
                    parts.append(f"Recent messages:\n" + "\n".join(recent_parts))
                
                full_context = "\n\n".join(parts) if parts else ""
                
                return {self.memory_key: full_context}
                
        except Exception as e:
            logger.error(f"Failed to load memory: {str(e)}")
            raise MemoryException(f"Load error: {str(e)}")
    
    def clear(self) -> None:
        """Clear all memory."""
        with self._lock:
            self.chat_history.clear()
            self.summary = ""
        logger.info("Cleared hybrid memory")


# Example usage:
# llm = OpenAI(api_key="...")
# memory = ConversationSummaryBufferMemory(
#     llm=llm,
#     buffer_size=3,  # Keep last 3 turns verbatim
#     max_token_limit=1500
# )
# 
# # After 10 conversations:
# # - Last 3 are in buffer (verbatim)
# # - First 7 are summarized