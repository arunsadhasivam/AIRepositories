"""
Base chain module for LLM processing pipelines.
Provides abstract interface for chain implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import time
import logging
logger = logging.getLogger(__name__)

@dataclass
class ChainMetrics:
    """
    Metrics for chain execution monitoring.
    
    Attributes:
        execution_time: Total execution time in seconds
        token_count: Total tokens used (if available)
        success: Whether execution was successful
        error_message: Error message if failed
    """
    execution_time: float
    token_count: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
