from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from rag.chain.ChainMetrics import ChainMetrics
import time
import logging
logger = logging.getLogger(__name__)

class BaseChain(ABC):
    """
    Abstract base class for all chain implementations.
    
    Chains process inputs through one or more steps to produce outputs.
    All chain implementations must implement the run method.
    """
    
    def __init__(self, name: str = "BaseChain", verbose: bool = False):
        """
        Initialize base chain.
        
        Args:
            name: Chain name for logging
            verbose: Whether to log detailed execution info
        """
        self.name = name
        self.verbose = verbose
        logger.info(f"Initialized {name}")
    
    @abstractmethod
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the chain with given inputs.
        
        Args:
            inputs: Input dictionary
            
        Returns:
            Output dictionary
            
        Raises:
            ChainException: If execution fails
        """
        pass
    
    def __call__(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make chain callable like a function.
        
        Args:
            inputs: Input dictionary
            
        Returns:
            Output dictionary
        """
        return self.run(inputs)
    
    def run_with_metrics(self, inputs: Dict[str, Any]) -> tuple[Dict[str, Any], ChainMetrics]:
        """
        Run chain and collect execution metrics.
        
        Args:
            inputs: Input dictionary
            
        Returns:
            Tuple of (outputs, metrics)
        """
        start_time = time.time()
        
        try:
            outputs = self.run(inputs)
            execution_time = time.time() - start_time
            
            metrics = ChainMetrics(
                execution_time=execution_time,
                success=True
            )
            
            if self.verbose:
                logger.info(f"{self.name} completed in {execution_time:.2f}s")
            
            return outputs, metrics
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            metrics = ChainMetrics(
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )
            
            logger.error(f"{self.name} failed after {execution_time:.2f}s: {str(e)}")
            
            raise
    
    def validate_inputs(self, inputs: Dict[str, Any], required_keys: List[str]) -> None:
        """
        Validate that required input keys are present.
        
        Args:
            inputs: Input dictionary
            required_keys: List of required keys
            
        Raises:
            ValueError: If required keys are missing
        """
        missing = set(required_keys) - set(inputs.keys())
        if missing:
            raise ValueError(f"Missing required input keys: {missing}")