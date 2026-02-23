
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import json


class MemoryException(Exception):
    """Custom exception for memory operations."""
    pass