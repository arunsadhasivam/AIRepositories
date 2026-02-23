from rag.filter.EmbeddingModelProtocol import EmbeddingModelProtocol
from rag.filter import ValidationRule
from rag.filter import FilterResult
from typing import Optional,List,Callable
from rag.retriever.Document import Document
import logging
logger = logging.getLogger(__name__)

class EmbeddingFilter:
    """
    Production-ready embedding-based document filter.
    
    Filters documents by semantic similarity to query.
    
    Attributes:
        embedding_model: Model for generating embeddings
        similarity_threshold: Minimum similarity score (0-1)
        distance_metric: Metric for similarity calculation
    """
    
    def __init__(self,
                 embedding_model: EmbeddingModelProtocol,
                 similarity_threshold: float = 0.7,
                 distance_metric: str = "cosine"):
        """
        Initialize embedding filter.
        
        Args:
            embedding_model: Embedding model instance
            similarity_threshold: Minimum similarity (0-1)
            distance_metric: 'cosine', 'euclidean', or 'dot_product'
            
        Raises:
            ValueError: If parameters are invalid
        """
        if embedding_model is None:
            raise ValueError("Embedding model cannot be None")
        if not 0 <= similarity_threshold <= 1:
            raise ValueError("Similarity threshold must be between 0 and 1")
        if distance_metric not in ['cosine', 'euclidean', 'dot_product']:
            raise ValueError(f"Invalid distance metric: {distance_metric}")
        
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
        self.distance_metric = distance_metric
        
        logger.info(
            f"EmbeddingFilter initialized: threshold={similarity_threshold}, "
            f"metric={distance_metric}"
        )
    
    def filter(self, query: str, documents: List[Document]) -> List[Document]:
        """
        Filter documents by similarity to query.
        
        Args:
            query: Query text
            documents: List of documents to filter
            
        Returns:
            List of documents above similarity threshold
        """
        if not documents:
            return []
        
        try:
            # Get query embedding
            query_embedding = self.embedding_model.embed_query(query)
            
            filtered_docs = []
            
            for doc in documents:
                # Get document embedding
                doc_embedding = self.embedding_model.embed_text(doc.content)
                
                # Calculate similarity
                similarity = self._calculate_similarity(query_embedding, doc_embedding)
                
                # Keep document if above threshold
                if similarity >= self.similarity_threshold:
                    # Update document score
                    doc.score = similarity
                    filtered_docs.append(doc)
            
            logger.debug(
                f"Filtered {len(documents)} documents to {len(filtered_docs)} "
                f"(threshold={self.similarity_threshold})"
            )
            
            return filtered_docs
            
        except Exception as e:
            logger.error(f"Embedding filter failed: {str(e)}")
            # Return original documents on error (fail-safe)
            return documents
    
    def _calculate_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Similarity score (0-1)
        """
        if self.distance_metric == "cosine":
            return self._cosine_similarity(vec1, vec2)
        elif self.distance_metric == "dot_product":
            return float(np.dot(vec1, vec2))
        else:  # euclidean
            distance = np.linalg.norm(vec1 - vec2)
            # Convert distance to similarity (inverse)
            return 1.0 / (1.0 + distance)
    
    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity."""
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        
        if norm_product == 0:
            return 0.0
        
        return float(dot_product / norm_product)


# Example usage:
# embedding_model = OpenAIEmbeddings()
# filter = EmbeddingFilter(
#     embedding_model=embedding_model,
#     similarity_threshold=0.75
# )
# 
# filtered_docs = filter.filter(
#     query="machine learning algorithms",
#     documents=retrieved_documents
# )