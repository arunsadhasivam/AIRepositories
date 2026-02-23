"""
Chat-based prompt template implementation for modern conversational models.
Supports role-based messages (system, user, assistant).
"""

from typing import List, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass, field


class MessageRole(Enum):
    """Enumeration of message roles in chat conversations."""
    SYSTEM = "system"  # System instructions/context
    USER = "user"  # User messages/queries
    ASSISTANT = "assistant"  # AI assistant responses
    FUNCTION = "function"  # Function call results (for some models)
