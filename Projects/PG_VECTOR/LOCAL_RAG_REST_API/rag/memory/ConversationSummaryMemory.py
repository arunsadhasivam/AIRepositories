"""
Summary memory that compresses old conversations.
Balances context preservation with memory efficiency.
"""

import logging
from rag.memory.BaseMemory import BaseMemory
from typing import Optional,Dict,Any,List
import threading
from rag.exception import MemoryException
from rag.memory import ConversationTurn
from rag.chain import LLMProtocol
logger = logging.getLogger(__name__)


class ConversationSummaryMemory(BaseMemory):
    """
    Production-ready summary memory implementation.
    
    Summarizes old conversations and keeps recent ones verbatim.
    
    Features:
    - Automatic summarization when history gets long
    - Configurable token limits
    - Preserves important context
    
    Suitable for:
    - Very long conversations
    - Context-critical applications
    - Token-constrained models
    
    Attributes:
        llm: Language model for generating summaries
        chat_history: Recent conversation turns
        summary: Summary of older conversations
        max_token_limit: Token threshold for summarization
    """
    
    def __init__(self,
                 llm: LLMProtocol,
                 memory_key: str = "history",
                 input_key: str = "input",
                 output_key: str = "output",
                 max_token_limit: int = 2000,
                 summary_message_count: int = 5):
        """
        Initialize summary memory.
        
        Args:
            llm: Language model for summarization
            memory_key: Key for memory in context
            input_key: Key for user input
            output_key: Key for AI output
            max_token_limit: Token limit before summarization
            summary_message_count: Messages to keep before summarizing rest
            
        Raises:
            ValueError: If parameters are invalid
        """
        super().__init__(memory_key, input_key, output_key)
        
        if llm is None:
            raise ValueError("LLM cannot be None")
        if max_token_limit < 100:
            raise ValueError("max_token_limit must be at least 100")
        if summary_message_count < 1:
            raise ValueError("summary_message_count must be at least 1")
        
        self.llm = llm
        self.max_token_limit = max_token_limit
        self.summary_message_count = summary_message_count
        
        self.chat_history: List[ConversationTurn] = []
        self.summary: str = ""
        self._lock = threading.Lock()
        
        logger.info(
            f"ConversationSummaryMemory initialized: "
            f"max_tokens={max_token_limit}, keep_messages={summary_message_count}"
        )
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        Save conversation turn and summarize if needed.
        
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
                self.chat_history.append(turn)
                
                # Check if summarization is needed
                if self._estimate_tokens() > self.max_token_limit:
                    self._summarize_history()
            
            logger.debug(f"Saved turn to memory (history size: {len(self.chat_history)})")
            
        except ValueError as ve:
            logger.error(f"Failed to save context: {str(ve)}")
            raise MemoryException(f"Save failed: {str(ve)}")
        except Exception as e:
            logger.error(f"Unexpected error saving context: {str(e)}")
            raise MemoryException(f"Save error: {str(e)}")
    
    def _estimate_tokens(self) -> int:
        """
        Estimate total token count (rough approximation).
        
        Returns:
            Estimated token count
        """
        # Rough estimate: 1 token ≈ 4 characters
        summary_chars = len(self.summary)
        history_chars = sum(
            len(turn.user_message) + len(turn.ai_message)
            for turn in self.chat_history
        )
        total_chars = summary_chars + history_chars
        return total_chars // 4
    
    def _summarize_history(self) -> None:
        """
        Summarize older messages to reduce token count.
        
        Keeps recent messages verbatim, summarizes older ones.
        """
        try:
            if len(self.chat_history) <= self.summary_message_count:
                return  # Not enough history to summarize
            
            # Split history into to_summarize and to_keep
            split_point = len(self.chat_history) - self.summary_message_count
            to_summarize = self.chat_history[:split_point]
            to_keep = self.chat_history[split_point:]
            
            # Format messages to summarize
            history_text = "\n".join([
                f"User: {turn.user_message}\nAssistant: {turn.ai_message}"
                for turn in to_summarize
            ])
            
            # Create summarization prompt
            summary_prompt = f"""Progressively summarize the following conversation, adding onto the previous summary.

Previous summary: {self.summary if self.summary else "None"}

New conversation to summarize:
{history_text}

Updated concise summary:"""
            
            # Generate summary using LLM
            new_summary = self.llm.generate(summary_prompt)
            
            # Update state
            self.summary = new_summary
            self.chat_history = to_keep
            
            logger.info(
                f"Summarized {len(to_summarize)} turns, "
                f"kept {len(to_keep)} recent turns"
            )
            
        except Exception as e:
            logger.error(f"Summarization failed: {str(e)}")
            # Don't raise exception - continue with current state
    
    def load_memory_variables(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Load summary and recent conversation history.
        
        Args:
            inputs: Optional input context (not used)
            
        Returns:
            Dictionary with summary and recent history
        """
        try:
            with self._lock:
                parts = []
                
                # Add summary if exists
                if self.summary:
                    parts.append(f"Summary of earlier conversation:\n{self.summary}")
                
                # Add recent messages
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
        """Clear all memory including summary."""
        with self._lock:
            self.chat_history.clear()
            self.summary = ""
        logger.info("Cleared summary memory")
    
    def get_summary(self) -> str:
        """Get current conversation summary."""
        with self._lock:
            return self.summary


# Example usage:
# llm = OpenAI(api_key="...")
# memory = ConversationSummaryMemory(
#     llm=llm,
#     max_token_limit=1000,
#     summary_message_count=3
# )
# 
# # After many conversations, old ones get summarized
# for i in range(20):
#     memory.save_context(
#         inputs={"input": f"Question {i}"},
#         outputs={"output": f"Answer {i}"}
#     )
# 
# # Memory contains: summary of first 17 + last 3 verbatim
# history = memory.load_memory_variables()