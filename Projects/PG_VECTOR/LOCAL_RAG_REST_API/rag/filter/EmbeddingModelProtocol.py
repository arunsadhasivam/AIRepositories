"""
Filter documents based on embedding similarity threshold.
Removes low-relevance documents from retrieval results.
"""

from typing import List, Protocol
import numpy as np


class EmbeddingModelProtocol(Protocol):
    """Protocol for embedding models."""
    
    def embed_query(self, text: str) -> np.ndarray:
        """Embed a query text."""
        ...
    
    def embed_text(self, text: str) -> np.ndarray:
        """Embed a document text."""
        ...

