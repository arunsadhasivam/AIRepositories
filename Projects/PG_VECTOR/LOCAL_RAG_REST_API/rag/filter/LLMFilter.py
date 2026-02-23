from rag.filter import ValidationRule
from rag.filter import FilterResult
from typing import Optional,List,Callable
import logging
logger = logging.getLogger(__name__)
class LLMFilter:
    """
    Production-ready LLM output filter.
    
    Validates and filters LLM outputs using configurable rules.
    
    Features:
    - Multiple validation rules
    - Content filtering
    - Length validation
    - Custom transformations
    
    Attributes:
        validation_rules: List of validation rules
        transformations: List of transformation functions
        strict_mode: Whether to fail on any validation error
    """
    
    def __init__(self,
                 validation_rules: Optional[List[ValidationRule]] = None,
                 transformations: Optional[List[Callable[[str], str]]] = None,
                 strict_mode: bool = True):
        """
        Initialize LLM filter.
        
        Args:
            validation_rules: List of validation rules
            transformations: List of transformation functions
            strict_mode: If True, fail on any validation error
        """
        self.validation_rules = validation_rules or []
        self.transformations = transformations or []
        self.strict_mode = strict_mode
        
        logger.info(
            f"LLMFilter initialized with {len(self.validation_rules)} rules, "
            f"strict_mode={strict_mode}"
        )
    
    def filter(self, llm_output: str) -> FilterResult:
        """
        Filter and validate LLM output.
        
        Args:
            llm_output: Raw LLM output
            
        Returns:
            FilterResult with validation status and filtered output
        """
        try:
            # Step 1: Validate output
            validation_errors = []
            
            for rule in self.validation_rules:
                is_valid, error_msg = rule.validate(llm_output)
                
                if not is_valid:
                    validation_errors.append(f"{rule.name}: {error_msg}")
                    
                    if self.strict_mode:
                        # Fail immediately in strict mode
                        return FilterResult(
                            valid=False,
                            output=None,
                            error_message=error_msg
                        )
            
            # Check if there were any validation errors (non-strict mode)
            if validation_errors and not self.strict_mode:
                logger.warning(f"Validation warnings: {validation_errors}")
            
            # Step 2: Apply transformations
            filtered_output = llm_output
            for transformation in self.transformations:
                try:
                    filtered_output = transformation(filtered_output)
                except Exception as e:
                    logger.error(f"Transformation failed: {str(e)}")
                    if self.strict_mode:
                        return FilterResult(
                            valid=False,
                            output=None,
                            error_message=f"Transformation error: {str(e)}"
                        )
            
            # Return successful result
            return FilterResult(
                valid=True,
                output=filtered_output,
                metadata={
                    'original_length': len(llm_output),
                    'filtered_length': len(filtered_output),
                    'transformations_applied': len(self.transformations)
                }
            )
            
        except Exception as e:
            logger.error(f"Filter execution failed: {str(e)}")
            return FilterResult(
                valid=False,
                output=None,
                error_message=f"Filter error: {str(e)}"
            )
    
    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule."""
        self.validation_rules.append(rule)
        logger.debug(f"Added validation rule: {rule.name}")
    
    def add_transformation(self, transformation: Callable[[str], str]) -> None:
        """Add a transformation function."""
        self.transformations.append(transformation)
        logger.debug("Added transformation function")


# Common validation rules
def create_length_rule(min_length: int = 1, max_length: int = 10000) -> ValidationRule:
    """Create a rule to validate output length."""
    def validator(text: str) -> bool:
        return min_length <= len(text) <= max_length
    
    return ValidationRule(
        name="length_check",
        validator=validator,
        error_message=f"Output length must be between {min_length} and {max_length}"
    )


def create_profanity_rule(profanity_list: List[str]) -> ValidationRule:
    """Create a rule to check for profanity."""
    def validator(text: str) -> bool:
        text_lower = text.lower()
        return not any(word in text_lower for word in profanity_list)
    
    return ValidationRule(
        name="profanity_check",
        validator=validator,
        error_message="Output contains inappropriate content"
    )


def create_format_rule(required_format: str) -> ValidationRule:
    """Create a rule to validate output format (e.g., must contain JSON)."""
    def validator(text: str) -> bool:
        if required_format == "json":
            import json
            try:
                json.loads(text)
                return True
            except:
                return False
        return True
    
    return ValidationRule(
        name="format_check",
        validator=validator,
        error_message=f"Output must be valid {required_format}"
    )


# Example usage:
# filter = LLMFilter(
#     validation_rules=[
#         create_length_rule(min_length=10, max_length=1000),
#         create_profanity_rule(["badword1", "badword2"])
#     ],
#     transformations=[
#         lambda text: text.strip(),  # Remove whitespace
#         lambda text: text.replace("\n\n\n", "\n\n")  # Normalize newlines
#     ]
# )
# 
# result = filter.filter(llm_output)
# if result.valid:
#     print(result.output)
# else:
#     print(f"Validation failed: {result.error_message}")