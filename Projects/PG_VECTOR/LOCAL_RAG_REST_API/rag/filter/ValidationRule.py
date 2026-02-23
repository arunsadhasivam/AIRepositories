from typing import Callable,Tuple,Optional
import logging
logger = logging.getLogger(__name__)
class ValidationRule:
    """
    Single validation rule for LLM output.
    
    Attributes:
        name: Rule identifier
        validator: Function that validates text
        error_message: Message to return if validation fails
    """
    
    def __init__(self,
                 name: str,
                 validator: Callable[[str], bool],
                 error_message: str):
        """
        Initialize validation rule.
        
        Args:
            name: Rule name
            validator: Function that returns True if valid
            error_message: Error message for failed validation
        """
        self.name = name
        self.validator = validator
        self.error_message = error_message
    
    def validate(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate text against this rule.
        
        Args:
            text: Text to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            is_valid = self.validator(text)
            return (is_valid, None if is_valid else self.error_message)
        except Exception as e:
            logger.error(f"Validation rule '{self.name}' failed: {str(e)}")
            return (False, f"Validation error: {str(e)}")