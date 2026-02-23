from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set
import re
import logging

logger = logging.getLogger(__name__)
class BasePromptTemplate(ABC):
    """
    Abstract base class for all prompt template implementations.
    
    Defines the contract for formatting prompts with variables.
    All template implementations must implement these methods.
    """
    
    def __init__(self, input_variables: List[str]):
        """
        Initialize prompt template.
        
        Args:
            input_variables: List of variable names required by template
        """
        self.input_variables = input_variables
        self._validate_variables()
        logger.debug(f"Initialized {self.__class__.__name__} with variables: {input_variables}")
    
    def _validate_variables(self) -> None:
        """
        Validate input variable names.
        
        Raises:
            ValueError: If variable names are invalid
        """
        if not self.input_variables:
            raise ValueError("Input variables list cannot be empty")
        
        # Check for duplicate variables
        if len(self.input_variables) != len(set(self.input_variables)):
            raise ValueError("Input variables contain duplicates")
        
        # Validate variable names (alphanumeric and underscore only)
        for var in self.input_variables:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', var):
                raise ValueError(
                    f"Invalid variable name '{var}': must start with letter/underscore "
                    "and contain only alphanumeric characters and underscores"
                )
    
    @abstractmethod
    def format(self, **kwargs: Any) -> Any:
        """
        Format template with given variables.
        
        Args:
            **kwargs: Variable values to substitute
            
        Returns:
            Formatted template (type depends on implementation)
            
        Raises:
            PromptTemplateException: If formatting fails
            ValueError: If required variables are missing
        """
        pass
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """
        Validate that all required variables are provided.
        
        Args:
            inputs: Dictionary of input variables
            
        Raises:
            ValueError: If required variables are missing or extra variables provided
        """
        # Check for missing variables
        missing = set(self.input_variables) - set(inputs.keys())
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
        
        # Check for extra variables (warning only, not error)
        extra = set(inputs.keys()) - set(self.input_variables)
        if extra:
            logger.warning(f"Extra variables provided (will be ignored): {extra}")
    
    def get_input_variables(self) -> List[str]:
        """
        Get list of required input variables.
        
        Returns:
            List of variable names
        """
        return self.input_variables.copy()