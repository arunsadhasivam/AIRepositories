"""
Base memory module for conversation history management.
Provides abstract interface for all memory implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import json


class BaseMemory(ABC):
    """
    Abstract base class for conversation memory implementations.
    
    Defines the contract for storing and retrieving conversation history.
    All memory implementations must implement these methods.
    
    Attributes:
        memory_key: Key name for memory in context
        input_key: Key for user input in save_context
        output_key: Key for AI output in save_context
    """
    
    def __init__(self,
                 memory_key: str = "history",
                 input_key: str = "input",
                 output_key: str = "output"):
        """
        Initialize base memory.
        
        Args:
            memory_key: Key name for memory in loaded variables
            input_key: Key for user input
            output_key: Key for AI output
        """
        self.memory_key = memory_key
        self.input_key = input_key
        self.output_key = output_key
        
        logger.debug(f"Initialized {self.__class__.__name__}")
    
    @abstractmethod
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        Save conversation turn to memory.
        
        Args:
            inputs: Dictionary containing user input
            outputs: Dictionary containing AI output
            
        Raises:
            MemoryException: If save fails
        """
        pass
    
    @abstractmethod
    def load_memory_variables(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Load conversation history from memory.
        
        Args:
            inputs: Optional input context for dynamic memory loading
            
        Returns:
            Dictionary with memory key and formatted history
            
        Raises:
            MemoryException: If load fails
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """
        Clear all memory.
        
        Warning: This operation cannot be undone!
        """
        pass
    
    def _extract_input(self, inputs: Dict[str, Any]) -> str:
        """
        Extract user input from inputs dictionary.
        
        Args:
            inputs: Inputs dictionary
            
        Returns:
            User input string
            
        Raises:
            ValueError: If input key not found
        """
        if self.input_key not in inputs:
            raise ValueError(f"Input key '{self.input_key}' not found in inputs")
        return str(inputs[self.input_key])
    
    def _extract_output(self, outputs: Dict[str, Any]) -> str:
        """
        Extract AI output from outputs dictionary.
        
        Args:
            outputs: Outputs dictionary
            
        Returns:
            AI output string
            
        Raises:
            ValueError: If output key not found
        """
        if self.output_key not in outputs:
            raise ValueError(f"Output key '{self.output_key}' not found in outputs")
        return str(outputs[self.output_key])