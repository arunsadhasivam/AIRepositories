"""
Simple string-based prompt template implementation.
Used for completion models and simple text formatting.
"""

from typing import Dict, Any,List,Tuple
import re
from  rag.templates.BasePromptTemplate import BasePromptTemplate
from rag.exception.PromptTemplateException import PromptTemplateException
import logging

logger = logging.getLogger(__name__)
class PromptTemplate(BasePromptTemplate):
    """
    Production-ready simple string prompt template.
    
    Formats a template string by replacing {variable} placeholders
    with actual values. Suitable for:
    - Simple text completion models
    - Legacy models without chat interface
    - Basic string formatting
    
    Attributes:
        template: Template string with {variable} placeholders
        template_format: Format type ('f-string' or 'jinja2')
    """
    
    def __init__(self,
                 template: str,
                 input_variables: List[str],
                 template_format: str = "f-string",
                 validate_template: bool = True):
        """
        Initialize simple prompt template.
        
        Args:
            template: Template string with {variable} placeholders
            input_variables: List of required variables
            template_format: Format type ('f-string' or 'jinja2')
            validate_template: Whether to validate template on initialization
            
        Raises:
            ValueError: If template is invalid
            PromptTemplateException: If initialization fails
        """
        super().__init__(input_variables)
        
        if not template or not template.strip():
            raise ValueError("Template cannot be empty")
        
        self.template = template
        self.template_format = template_format
        
        if validate_template:
            self._validate_template()
        
        logger.info(f"PromptTemplate initialized with {len(input_variables)} variables")
    
    def _validate_template(self) -> None:
        """
        Validate that template contains all declared variables.
        
        Raises:
            ValueError: If template validation fails
        """
        # Extract variables from template
        found_variables = set(re.findall(r'\{(\w+)\}', self.template))
        
        # Check if all declared variables are in template
        declared_vars = set(self.input_variables)
        missing_in_template = declared_vars - found_variables
        if missing_in_template:
            logger.warning(
                f"Variables declared but not found in template: {missing_in_template}"
            )
        
        # Check if template has undeclared variables
        undeclared = found_variables - declared_vars
        if undeclared:
            raise ValueError(
                f"Template contains undeclared variables: {undeclared}. "
                "Add them to input_variables list."
            )
    
    def format(self, **kwargs: Any) -> str:
        """
        Format template by replacing placeholders with values.
        
        Args:
            **kwargs: Variable values
            
        Returns:
            Formatted template string
            
        Raises:
            ValueError: If required variables are missing
            PromptTemplateException: If formatting fails
        """
        try:
            # Validate inputs
            self.validate_inputs(kwargs)
            
            # Format template
            if self.template_format == "f-string":
                result = self._format_fstring(kwargs)
            elif self.template_format == "jinja2":
                result = self._format_jinja2(kwargs)
            else:
                raise ValueError(f"Unknown template format: {self.template_format}")
            
            logger.debug(f"Formatted prompt: {len(result)} characters")
            
            return result
            
        except ValueError as ve:
            logger.error(f"Template formatting validation error: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"Template formatting failed: {str(e)}")
            raise PromptTemplateException(f"Formatting error: {str(e)}")
    
    def _format_fstring(self, values: Dict[str, Any]) -> str:
        """
        Format template using f-string style substitution.
        
        Args:
            values: Variable values
            
        Returns:
            Formatted string
        """
        result = self.template
        
        # Replace each variable
        for key, value in values.items():
            # Convert value to string
            str_value = str(value)
            
            # Replace all occurrences of {key}
            result = result.replace(f"{{{key}}}", str_value)
        
        return result
    
    def _format_jinja2(self, values: Dict[str, Any]) -> str:
        """
        Format template using Jinja2 templating engine.
        
        Args:
            values: Variable values
            
        Returns:
            Formatted string
            
        Raises:
            ImportError: If jinja2 is not installed
            PromptTemplateException: If Jinja2 rendering fails
        """
        try:
            from jinja2 import Template
        except ImportError:
            raise ImportError(
                "jinja2 is required for jinja2 template format. "
                "Install it with: pip install jinja2"
            )
        
        try:
            jinja_template = Template(self.template)
            result = jinja_template.render(**values)
            return result
        except Exception as e:
            raise PromptTemplateException(f"Jinja2 rendering failed: {str(e)}")
    
    @classmethod
    def from_template(cls, template: str, **kwargs) -> 'PromptTemplate':
        """
        Create PromptTemplate by auto-detecting variables from template.
        
        Args:
            template: Template string
            **kwargs: Additional arguments for PromptTemplate
            
        Returns:
            PromptTemplate instance
        """
        # Extract variables from template
        variables = list(set(re.findall(r'\{(\w+)\}', template)))
        
        return cls(
            template=template,
            input_variables=variables,
            **kwargs
        )


# Example usage:
# template = PromptTemplate(
#     template="Translate the following {language} text to English:\n\n{text}",
#     input_variables=["language", "text"]
# )
# prompt = template.format(language="French", text="Bonjour le monde")
# Output: "Translate the following French text to English:\n\nBonjour le monde"