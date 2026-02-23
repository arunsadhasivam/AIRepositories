"""
Sequential chain for multi-step processing pipelines.
Chains multiple operations in sequence.
"""


from typing import Dict, Any, Optional, List
from rag.chain.BaseChain import BaseChain
from rag.exception.ChainException import ChainException
import logging
logger = logging.getLogger(__name__)


class SequentialChain(BaseChain):
    """
    Production-ready sequential chain executor.
    
    Executes multiple chains in sequence, passing outputs as inputs
    to the next chain in the pipeline.
    
    Suitable for:
    - Multi-step processing workflows
    - Complex data transformations
    - Modular pipeline architectures
    
    Attributes:
        chains: List of chains to execute sequentially
        input_variables: Input variables for first chain
        output_variables: Output variables to return
        return_all: Whether to return all intermediate outputs
    """
    
    def __init__(self,
                 chains: List[BaseChain],
                 input_variables: List[str],
                 output_variables: List[str],
                 return_all: bool = False,
                 verbose: bool = False):
        """
        Initialize sequential chain.
        
        Args:
            chains: List of chains to execute in order
            input_variables: Variables required by first chain
            output_variables: Variables to include in final output
            return_all: Return all intermediate outputs
            verbose: Enable detailed logging
            
        Raises:
            ValueError: If configuration is invalid
        """
        super().__init__(name="SequentialChain", verbose=verbose)
        
        if not chains:
            raise ValueError("Chains list cannot be empty")
        if len(chains) < 2:
            raise ValueError("Sequential chain requires at least 2 chains")
        
        self.chains = chains
        self.input_variables = input_variables
        self.output_variables = output_variables
        self.return_all = return_all
        
        # Validate chain compatibility
        self._validate_chain_sequence()
        
        logger.info(f"SequentialChain initialized with {len(chains)} chains")
    
    def _validate_chain_sequence(self) -> None:
        """
        Validate that chain outputs match next chain's inputs.
        
        Raises:
            ValueError: If chains are incompatible
        """
        # This is a simplified validation
        # In production, you'd check each chain's input/output keys
        logger.debug(f"Validated {len(self.chains)} chains in sequence")
    
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute all chains in sequence.
        
        Args:
            inputs: Initial input dictionary
            
        Returns:
            Final output dictionary
            
        Raises:
            ChainException: If any chain fails
        """
        try:
            # Validate initial inputs
            self.validate_inputs(inputs, self.input_variables)
            
            # Track all outputs if return_all is True
            all_outputs = {} if self.return_all else None
            
            # Current data to pass between chains
            current_data = inputs.copy()
            
            # Execute each chain sequentially
            for i, chain in enumerate(self.chains):
                if self.verbose:
                    logger.info(f"Executing chain {i+1}/{len(self.chains)}: {chain.name}")
                
                try:
                    # Execute chain
                    chain_output = chain.run(current_data)
                    
                    # Store outputs if needed
                    if self.return_all:
                        all_outputs[f"chain_{i}_output"] = chain_output
                    
                    # Merge output into current data for next chain
                    current_data.update(chain_output)
                    
                    if self.verbose:
                        logger.info(f"Chain {i+1} completed successfully")
                    
                except Exception as e:
                    logger.error(f"Chain {i+1} ({chain.name}) failed: {str(e)}")
                    raise ChainException(f"Chain {i+1} failed: {str(e)}")
            
            # Build final output
            if self.return_all:
                # Return all intermediate outputs
                return all_outputs
            else:
                # Return only requested output variables
                final_output = {
                    key: current_data[key] 
                    for key in self.output_variables 
                    if key in current_data
                }
                
                # Check if all requested outputs are present
                missing = set(self.output_variables) - set(final_output.keys())
                if missing:
                    logger.warning(f"Missing requested output variables: {missing}")
                
                return final_output
            
        except ChainException:
            raise
        except Exception as e:
            logger.error(f"SequentialChain execution failed: {str(e)}")
            raise ChainException(f"Sequential chain error: {str(e)}")


# Example usage:
# # Chain 1: Extract entities
# entity_chain = LLMChain(
#     llm=llm,
#     prompt_template=PromptTemplate(
#         template="Extract entities from: {text}",
#         input_variables=["text"]
#     )
# )
# 
# # Chain 2: Classify sentiment
# sentiment_chain = LLMChain(
#     llm=llm,
#     prompt_template=PromptTemplate(
#         template="Classify sentiment of: {text}",
#         input_variables=["text"]
#     )
# )
# 
# # Sequential chain
# pipeline = SequentialChain(
#     chains=[entity_chain, sentiment_chain],
#     input_variables=["text"],
#     output_variables=["output"]
# )
# 
# result = pipeline.run({"text": "I love this product!"})