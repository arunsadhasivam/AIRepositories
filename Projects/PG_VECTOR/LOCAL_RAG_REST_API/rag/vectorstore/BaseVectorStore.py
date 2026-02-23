from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import numpy as np
from enum import Enum
from rag.vectorstore.DistanceMetric import DistanceMetric
from rag.retriever.Document import Document

import logging
logger = logging.getLogger(__name__)
class BaseVectorStore(ABC):
    """
    Abstract base class for vector database implementations.
    
    Defines the contract for storing, searching, and managing
    vector embeddings. All vector store implementations must
    implement these methods.
    """
    
    def __init__(self, 
                 collection_name: str,
                 distance_metric: DistanceMetric = DistanceMetric.COSINE):
        """
        Initialize vector store.
        
        Args:
            collection_name: Name of the collection/index
            distance_metric: Distance metric for similarity search
        """
        self.collection_name = collection_name
        self.distance_metric = distance_metric
        logger.info(
            f"Initialized {self.__class__.__name__} with collection '{collection_name}'"
        )
    
    @abstractmethod
    def add_documents(self, 
                     documents: List[Document], 
                     embeddings: List[np.ndarray],
                     batch_size: int = 100) -> None:
        """
        Add documents with their embeddings to the vector store.
        
        Args:
            documents: List of documents to add
            embeddings: Corresponding embedding vectors
            batch_size: Number of documents to process per batch
            
        Raises:
            VectorStoreException: If addition fails
            ValueError: If documents and embeddings lengths don't match
        """
        pass
    
    @abstractmethod
    def similarity_search(self, 
                         query_embedding: np.ndarray, 
                         k: int = 5,
                         filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Search for similar documents using query embedding.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            filter: Optional metadata filters
            
        Returns:
            List of similar documents with scores
            
        Raises:
            VectorStoreException: If search fails
        """
        pass
    
    @abstractmethod
    def delete_documents(self, ids: List[str]) -> int:
        """
        Delete documents by their IDs.
        
        Args:
            ids: List of document IDs to delete
            
        Returns:
            Number of documents successfully deleted
            
        Raises:
            VectorStoreException: If deletion fails
        """
        pass
    
    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[Document]:
        """
        Retrieve a single document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document if found, None otherwise
        """
        pass
    
    @abstractmethod
    def count_documents(self) -> int:
        """
        Get total number of documents in the store.
        
        Returns:
            Total document count
        """
        pass
    
    def validate_embedding(self, embedding: np.ndarray, expected_dim: Optional[int] = None) -> None:
        """
        Validate embedding vector.
        
        Args:
            embedding: Embedding vector to validate
            expected_dim: Expected dimension (if known)
            
        Raises:
            ValueError: If embedding is invalid
        """
        if embedding is None:
            raise ValueError("Embedding cannot be None")
        
        if not isinstance(embedding, np.ndarray):
            raise ValueError("Embedding must be a numpy array")
        
        if embedding.size == 0:
            raise ValueError("Embedding cannot be empty")
        
        if expected_dim is not None and len(embedding) != expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {expected_dim}, "
                f"got {len(embedding)}"
            )
        
        # Check for NaN or Inf values
        if not np.isfinite(embedding).all():
            raise ValueError("Embedding contains NaN or Inf values")