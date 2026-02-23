"""
Filter and validate LLM outputs before returning to user.
Ensures quality and safety of LLM responses.
"""

from typing import List, Callable, Tuple, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class FilterResult:
    """
    Result of filter validation.
    
    Attributes:
        valid: Whether output passed validation
        output: Filtered/modified output
        error_message: Error message if validation failed
        metadata: Additional metadata from filtering
    """
    valid: bool
    output: Optional[str]
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
