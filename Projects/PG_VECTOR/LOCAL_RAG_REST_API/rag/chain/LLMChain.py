from rag.chain.BaseChain import BaseChain
from rag.chain.LLMProtocol import LLMProtocol
from rag.templates import BasePromptTemplate,ChatPromptTemplate
from typing import List, Optional, Dict, Any
from rag.exception.ChainException import ChainException
import logging
import time
logger = logging.getLogger(__name__)

class LLMChain(BaseChain):
    """
    Production-ready basic LLM chain.
    
    Executes: Prompt Template → Format → LLM → Response
    
    Suitable for:
    - Single-turn interactions
    - Simple text generation
    - Stateless operations
    
    Attributes:
        llm: Language model instance
        prompt_template: Prompt template for formatting
        output_key: Key name for output in result dict
        llm_kwargs: Additional arguments for LLM calls
    """
    
    def __init__(self,
                 llm: LLMProtocol,
                 prompt_template: BasePromptTemplate,
                 output_key: str = "output",
                 llm_kwargs: Optional[Dict[str, Any]] = None,
                 retry_count: int = 3,
                 verbose: bool = False):
        """
        Initialize LLM chain.
        
        Args:
            llm: Language model instance
            prompt_template: Template for formatting prompts
            output_key: Key for output in result dictionary
            llm_kwargs: Additional LLM parameters (temperature, max_tokens, etc.)
            retry_count: Number of retries on failure
            verbose: Enable detailed logging
            
        Raises:
            ValueError: If inputs are invalid
        """
        super().__init__(name="LLMChain", verbose=verbose)
        
        if llm is None:
            raise ValueError("LLM cannot be None")
        if prompt_template is None:
            raise ValueError("Prompt template cannot be None")
        
        self.llm = llm
        self.prompt_template = prompt_template
        self.output_key = output_key
        self.llm_kwargs = llm_kwargs or {}
        self.retry_count = retry_count
        
        logger.info(
            f"LLMChain initialized with {len(prompt_template.get_input_variables())} "
            f"input variables"
        )
    
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute LLM chain: format prompt → call LLM → return response.
        
        Args:
            inputs: Input variables for prompt template
            
        Returns:
            Dictionary with LLM response
            
        Raises:
            ChainException: If execution fails
        """
        try:
            # Step 1: Format prompt with input variables
            if isinstance(self.prompt_template, ChatPromptTemplate):
                # For chat models
                messages = self.prompt_template.format(**inputs)
                
                if self.verbose:
                    logger.info(f"Formatted {len(messages)} chat messages")
                
                # Step 2: Call LLM with formatted messages
                response = self._call_llm_with_retry(
                    lambda: self.llm.chat(messages, **self.llm_kwargs)
                )
            else:
                # For completion models
                prompt = self.prompt_template.format(**inputs)
                
                if self.verbose:
                    logger.info(f"Formatted prompt: {len(prompt)} characters")
                
                # Step 2: Call LLM with formatted prompt
                response = self._call_llm_with_retry(
                    lambda: self.llm.generate(prompt, **self.llm_kwargs)
                )
            
            # Step 3: Return response in standard format
            result = {self.output_key: response}
            
            if self.verbose:
                logger.info(f"LLM response: {len(response)} characters")
            
            return result
            
        except Exception as e:
            logger.error(f"LLMChain execution failed: {str(e)}")
            raise ChainException(f"Chain execution error: {str(e)}")
    
    def _call_llm_with_retry(self, llm_call: callable) -> str:
        """
        Call LLM with retry logic for production reliability.
        
        Args:
            llm_call: Callable that makes the LLM API call
            
        Returns:
            LLM response text
            
        Raises:
            ChainException: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.retry_count):
            try:
                response = llm_call()
                
                # Validate response
                if response is None or (isinstance(response, str) and not response.strip()):
                    raise ValueError("LLM returned empty response")
                
                return response
                
            except Exception as e:
                last_error = e
                logger.warning(f"LLM call attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.retry_count - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
        
        raise ChainException(f"LLM call failed after {self.retry_count} attempts: {str(last_error)}")
    
    def predict(self, **kwargs: Any) -> str:
        """
        Convenience method for simple prediction.
        
        Args:
            **kwargs: Input variables
            
        Returns:
            LLM response string
        """
        result = self.run(kwargs)
        return result[self.output_key]


# Example usage:
# llm = OpenAI(api_key="...")
# template = PromptTemplate(
#     template="Translate {text} to {language}",
#     input_variables=["text", "language"]
# )
# chain = LLMChain(llm=llm, prompt_template=template)
# result = chain.run({"text": "Hello", "language": "Spanish"})
# Output: {"output": "Hola"}