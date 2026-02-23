from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from rag.retriever.Document import Document
from rag.exception.RetrieverException import RetrieverException
import logging

# Configure logging for production monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BaseRetriever(ABC):
    """
    Abstract base class for all document retrieval implementations.
    
    This class defines the contract that all retrievers must implement.
    Subclasses can implement different retrieval strategies (keyword-based,
    vector-based, hybrid, etc.) while maintaining a consistent interface.
    """
    
    def __init__(self, name: str = "BaseRetriever"):
        """
        Initialize the base retriever.
        
        Args:
            name: Identifier for this retriever instance (for logging)
        """
        self.name = name
        logger.info(f"Initialized {self.name}")
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
        """
        Core retrieval method that must be implemented by all subclasses.
        
        Args:
            query: Search query string
            top_k: Maximum number of documents to return
            
        Returns:
            List of relevant documents, ordered by relevance (highest first)
            
        Raises:
            RetrieverException: If retrieval fails
            ValueError: If query is invalid
        """
        pass
    
    def retrieve_with_scores(self, query: str, top_k: int = 5) -> List[tuple[Document, float]]:
        """
        Retrieve documents with explicit relevance scores.
        
        Args:
            query: Search query string
            top_k: Maximum number of documents to return
            
        Returns:
            List of tuples containing (document, relevance_score)
        """
        try:
            # Get documents using the main retrieve method
            documents = self.retrieve(query, top_k)
            
            # Return documents with their scores
            return [(doc, doc.score if doc.score is not None else 0.0) 
                    for doc in documents]
        except Exception as e:
            logger.error(f"Error in retrieve_with_scores: {str(e)}")
            raise RetrieverException(f"Failed to retrieve with scores: {str(e)}")
    
    def validate_query(self, query: str) -> None:
        """
        Validate query input before processing.
        
        Args:
            query: Query string to validate
            
        Raises:
            ValueError: If query is invalid
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        
        if len(query) > 10000:  # Reasonable upper limit
            raise ValueError("Query exceeds maximum length of 10000 characters")
    
    def log_retrieval(self, query: str, num_results: int) -> None:
        """
        Log retrieval operation for monitoring and debugging.
        
        Args:
            query: The query that was executed
            num_results: Number of results returned
        """
        logger.info(
            f"[{self.name}] Retrieved {num_results} documents for query: "
            f"'{query[:50]}{'...' if len(query) > 50 else ''}'"
        )