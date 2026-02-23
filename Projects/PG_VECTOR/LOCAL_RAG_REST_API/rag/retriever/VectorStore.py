
from typing import Protocol, List,Dict,Any
from rag.retriever.Document import Document

import numpy as np
class VectorStore(Protocol):
    """
    Protocol defining the interface for vector stores.
    Any vector database should implement these methods.
    """
    
    def add_documents(self, documents: List[Document], embeddings: List[np.ndarray]) -> None:
        """Add documents with their embeddings."""
        ...
    
    def similarity_search(self, query_embedding: np.ndarray, k: int) -> List[Document]:
        """Search for similar documents."""
        ...