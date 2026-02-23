

from typing import Protocol, List,Dict,Any
import numpy as np
class EmbeddingModel(Protocol):
    """
    Protocol defining the interface for embedding models.
    Any embedding model implementation should follow this interface.
    """
    
    def embed_query(self, text: str) -> np.ndarray:
        """Embed a single query text into a vector."""
        ...
    
    def embed_documents(self, texts: List[str]) -> List[np.ndarray]:
        """Embed multiple documents into vectors."""
        ...
