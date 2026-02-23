"""
Few-shot prompt template with example demonstrations.
Useful for teaching models through examples.
"""

from typing import List, Dict, Any, Optional

from dataclasses import dataclass, field
from rag.templates import BasePromptTemplate,PromptTemplate
from rag.message.ChatMessage import ChatMessage
from rag.exception.PromptTemplateException import PromptTemplateException
import logging
logger = logging.getLogger(__name__)
class FewShotPromptTemplate(BasePromptTemplate):
    """
    Production-ready few-shot prompt template.
    
    Includes example demonstrations to guide the model's behavior.
    Suitable for:
    - Tasks requiring examples (classification, extraction)
    - Teaching specific output formats
    - Improving consistency
    
    Attributes:
        examples: List of example input-output pairs
        example_template: Template for formatting each example
        prefix: Text before examples
        suffix: Text after examples (includes final question)
        example_separator: Separator between examples
    """
    
    def __init__(self,
                 examples: List[Dict[str, str]],
                 example_template: PromptTemplate,
                 prefix: str,
                 suffix: str,
                 input_variables: List[str],
                 example_separator: str = "\n\n",
                 validate_examples: bool = True):
        """
        Initialize few-shot prompt template.
        
        Args:
            examples: List of example dictionaries
            example_template: Template for formatting each example
            prefix: Text before examples
            suffix: Text after examples with {variables}
            input_variables: Variables in suffix
            example_separator: String to separate examples
            validate_examples: Whether to validate examples on init
            
        Raises:
            ValueError: If configuration is invalid
        """
        super().__init__(input_variables)
        
        if not examples:
            raise ValueError("Examples list cannot be empty")
        
        self.examples = examples
        self.example_template = example_template
        self.prefix = prefix
        self.suffix = suffix
        self.example_separator = example_separator
        
        if validate_examples:
            self._validate_examples()
        
        logger.info(
            f"FewShotPromptTemplate initialized with {len(examples)} examples, "
            f"{len(input_variables)} variables"
        )
    
    def _validate_examples(self) -> None:
        """
        Validate that all examples have required fields.
        
        Raises:
            ValueError: If examples are invalid
        """
        example_vars = set(self.example_template.get_input_variables())
        
        for i, example in enumerate(self.examples):
            example_keys = set(example.keys())
            missing = example_vars - example_keys
            
            if missing:
                raise ValueError(
                    f"Example {i} missing required fields: {missing}"
                )
    
    def format(self, **kwargs: Any) -> str:
        """
        Format few-shot prompt with examples and final question.
        
        Args:
            **kwargs: Variable values for suffix
            
        Returns:
            Complete formatted prompt with examples
            
        Raises:
            ValueError: If required variables are missing
            PromptTemplateException: If formatting fails
        """
        try:
            # Validate inputs
            self.validate_inputs(kwargs)
            
            # Build prompt parts
            parts = []
            
            # Add prefix
            if self.prefix:
                parts.append(self.prefix)
            
            # Format and add each example
            for example in self.examples:
                formatted_example = self.example_template.format(**example)
                parts.append(formatted_example)
            
            # Format and add suffix
            formatted_suffix = self._format_suffix(kwargs)
            parts.append(formatted_suffix)
            
            # Join all parts
            result = self.example_separator.join(parts)
            
            logger.debug(
                f"Formatted few-shot prompt: {len(self.examples)} examples, "
                f"{len(result)} characters"
            )
            
            return result
            
        except ValueError as ve:
            logger.error(f"Few-shot template validation error: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"Few-shot template formatting failed: {str(e)}")
            raise PromptTemplateException(f"Formatting error: {str(e)}")
    
    def _format_suffix(self, values: Dict[str, Any]) -> str:
        """
        Format suffix with variables.
        
        Args:
            values: Variable values
            
        Returns:
            Formatted suffix
        """
        result = self.suffix
        
        for key, value in values.items():
            result = result.replace(f"{{{key}}}", str(value))
        
        return result
    
    def add_example(self, example: Dict[str, str]) -> None:
        """
        Add a new example to the template.
        
        Args:
            example: Example dictionary
            
        Raises:
            ValueError: If example is invalid
        """
        # Validate example has required fields
        example_vars = set(self.example_template.get_input_variables())
        example_keys = set(example.keys())
        missing = example_vars - example_keys
        
        if missing:
            raise ValueError(f"Example missing required fields: {missing}")
        
        self.examples.append(example)
        logger.debug(f"Added example to template (total: {len(self.examples)})")
    
    def remove_example(self, index: int) -> None:
        """
        Remove an example by index.
        
        Args:
            index: Index of example to remove
            
        Raises:
            IndexError: If index is out of range
        """
        if index < 0 or index >= len(self.examples):
            raise IndexError(f"Example index {index} out of range")
        
        self.examples.pop(index)
        logger.debug(f"Removed example at index {index}")
    
    @classmethod
    def from_examples(cls,
                      examples: List[Dict[str, str]],
                      prefix: str,
                      suffix: str,
                      input_variables: List[str],
                      example_separator: str = "\n\n",
                      **kwargs) -> 'FewShotPromptTemplate':
        """
        Create FewShotPromptTemplate with auto-generated example template.
        
        Args:
            examples: List of example dictionaries
            prefix: Text before examples
            suffix: Text after examples
            input_variables: Variables in suffix
            example_separator: Separator between examples
            **kwargs: Additional arguments
            
        Returns:
            FewShotPromptTemplate instance
        """
        # Auto-detect example variables from first example
        if not examples:
            raise ValueError("Examples list cannot be empty")
        
        example_vars = list(examples[0].keys())
        
        # Create simple example template
        example_template_str = "\n".join(
            f"{var}: {{{var}}}" for var in example_vars
        )
        
        example_template = PromptTemplate(
            template=example_template_str,
            input_variables=example_vars
        )
        
        return cls(
            examples=examples,
            example_template=example_template,
            prefix=prefix,
            suffix=suffix,
            input_variables=input_variables,
            example_separator=example_separator,
            **kwargs
        )


# Example usage:
# examples = [
#     {"input": "2 + 2", "output": "4"},
#     {"input": "5 * 3", "output": "15"},
#     {"input": "10 - 4", "output": "6"}
# ]
#
# example_template = PromptTemplate(
#     template="Q: {input}\nA: {output}",
#     input_variables=["input", "output"]
# )
#
# template = FewShotPromptTemplate(
#     examples=examples,
#     example_template=example_template,
#     prefix="Solve the following math problems:",
#     suffix="Q: {input}\nA:",
#     input_variables=["input"]
# )
#
# prompt = template.format(input="7 + 8")
# Output:
# Solve the following math problems:
#
# Q: 2 + 2
# A: 4
#
# Q: 5 * 3
# A: 15
#
# Q: 10 - 4
# A: 6
#
# Q: 7 + 8
# A: