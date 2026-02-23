"""
Conversation chain with memory for multi-turn dialogues.
Maintains conversation history across interactions.
"""

from typing import Dict, Any, Optional, List
from rag.chain import BaseChain
from rag.templates.PromptTemplate import ChatPromptTemplate
from rag.chain.LLMProtocol import LLMProtocol
from rag.memory.BaseMemory import BaseMemory
from rag.exception.ChainException import ChainException
import time
import logging
logger = logging.getLogger(__name__)

class ConversationChain(BaseChain):
    """
    Production-ready conversation chain with memory.
    
    Executes: Load Memory → Format Prompt → LLM → Save to Memory → Response
    
    Suitable for:
    - Multi-turn conversations
    - Chatbots and assistants
    - Context-aware dialogues
    
    Attributes:
        llm: Language model instance
        memory: Conversation memory instance
        prompt_template: Chat prompt template
        input_key: Key for user input in inputs dict
        output_key: Key for AI output in result dict
    """
    
    def __init__(self,
                 llm: LLMProtocol,
                 memory: 'BaseMemory',
                 prompt_template: ChatPromptTemplate,
                 input_key: str = "input",
                 output_key: str = "output",
                 llm_kwargs: Optional[Dict[str, Any]] = None,
                 verbose: bool = False):
        """
        Initialize conversation chain.
        
        Args:
            llm: Language model instance
            memory: Memory instance for conversation history
            prompt_template: Chat template with history placeholder
            input_key: Key for user input
            output_key: Key for AI output
            llm_kwargs: Additional LLM parameters
            verbose: Enable detailed logging
            
        Raises:
            ValueError: If inputs are invalid
        """
        super().__init__(name="ConversationChain", verbose=verbose)
        
        if llm is None:
            raise ValueError("LLM cannot be None")
        if memory is None:
            raise ValueError("Memory cannot be None")
        if prompt_template is None:
            raise ValueError("Prompt template cannot be None")
        
        self.llm = llm
        self.memory = memory
        self.prompt_template = prompt_template
        self.input_key = input_key
        self.output_key = output_key
        self.llm_kwargs = llm_kwargs or {}
        
        logger.info("ConversationChain initialized with memory")
    
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute conversation chain with memory.
        
        Steps:
        1. Load conversation history from memory
        2. Combine with current input
        3. Format prompt with history
        4. Call LLM
        5. Save interaction to memory
        6. Return response
        
        Args:
            inputs: Input dictionary with user message
            
        Returns:
            Dictionary with AI response
            
        Raises:
            ChainException: If execution fails
        """
        try:
            # Validate required input
            if self.input_key not in inputs:
                raise ValueError(f"Missing required input key: {self.input_key}")
            
            user_input = inputs[self.input_key]
            
            # Step 1: Load conversation history from memory
            memory_variables = self.memory.load_memory_variables()
            
            if self.verbose:
                logger.info(f"Loaded memory: {len(str(memory_variables))} characters")
            
            # Step 2: Combine current input with memory
            all_inputs = {**memory_variables, **inputs}
            
            # Step 3: Format prompt with history and current input
            messages = self.prompt_template.format(**all_inputs)
            
            if self.verbose:
                logger.info(f"Formatted conversation with {len(messages)} messages")
            
            # Step 4: Call LLM
            response = self._call_llm_safely(messages)
            
            if self.verbose:
                logger.info(f"LLM response: {len(response)} characters")
            
            # Step 5: Save interaction to memory
            self.memory.save_context(
                inputs={self.input_key: user_input},
                outputs={self.output_key: response}
            )
            
            if self.verbose:
                logger.info("Saved interaction to memory")
            
            # Step 6: Return response
            return {self.output_key: response}
            
        except Exception as e:
            logger.error(f"ConversationChain execution failed: {str(e)}")
            raise ChainException(f"Conversation chain error: {str(e)}")
    
    def _call_llm_safely(self, messages: List[Dict[str, str]]) -> str:
        """
        Call LLM with error handling.
        
        Args:
            messages: Formatted chat messages
            
        Returns:
            LLM response
            
        Raises:
            ChainException: If LLM call fails
        """
        try:
            response = self.llm.chat(messages, **self.llm_kwargs)
            
            if not response or not response.strip():
                raise ValueError("LLM returned empty response")
            
            return response
            
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise ChainException(f"LLM error: {str(e)}")
    
    def predict(self, user_input: str) -> str:
        """
        Convenience method for simple conversation.
        
        Args:
            user_input: User message
            
        Returns:
            AI response string
        """
        result = self.run({self.input_key: user_input})
        return result[self.output_key]
    
    def clear_memory(self) -> None:
        """Clear conversation history."""
        self.memory.clear()
        logger.info("Cleared conversation memory")
    
    def get_conversation_history(self) -> str:
        """
        Get formatted conversation history.
        
        Returns:
            Formatted history string
        """
        memory_vars = self.memory.load_memory_variables()
        # Assuming memory returns history under a standard key
        return memory_vars.get('history', '')


# Example usage:
# llm = OpenAI(api_key="...")
# memory = ConversationBufferMemory()
# template = ChatPromptTemplate.from_messages([
#     ("system", "You are a helpful assistant."),
#     ("user", "{history}\n{input}")
# ])
# chain = ConversationChain(llm=llm, memory=memory, prompt_template=template)
# 
# response1 = chain.predict("Hi, I'm John")
# # AI: "Hello John! How can I help you today?"
# 
# response2 = chain.predict("What's my name?")
# # AI: "Your name is John."