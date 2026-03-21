from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

# Configure logging for production monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Document:
    """
    Represents a document with content and metadata.
    
    Attributes:
        id: Unique identifier for the document
        content: Main text content of the document
        metadata: Additional information (source, timestamp, etc.)
        score: Relevance score from retrieval (optional)
    """
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: Optional[float] = None
    page_content: Optional[str] = None   

    def __post_init__(self):
        """Validate document after initialization."""
        if not self.id:
            raise ValueError("Document ID cannot be empty")
        if not self.content:
            raise ValueError("Document content cannot be empty")
        
        self.page_content = self.content  
        
        # Add creation timestamp if not present in metadata
        if 'created_at' not in self.metadata:
            self.metadata['created_at'] = datetime.utcnow().isoformat()


class RetrieverException(Exception):
    """Custom exception for retriever-related errors."""
    pass
