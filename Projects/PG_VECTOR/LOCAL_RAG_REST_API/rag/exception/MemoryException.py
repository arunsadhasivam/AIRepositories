
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)


class MemoryException(Exception):
    """Memory exception for memory operations."""
     
    def __init__(self, message: str, cause: Exception = None):
        # Call parent Exception constructor with message
        super().__init__(message)
        # Store original cause for chaining
        self.cause = cause
        # Log error when exception is created
        logger.error(f"MemoryException: {message}" + (f" | Cause: {str(cause)}" if cause else ""))
