"""
Vector-based semantic retriever using dense embeddings.
Provides similarity search using cosine distance in vector space.
"""

from typing import Protocol, List,Dict,Any
import numpy as np
from rag.retriever.BaseRetriever import BaseRetriever
from rag.retriever.Document import Document
import logging
from rag.exception.RetrieverException import RetrieverException
from rag.retriever  import EmbeddingModel,VectorStoreRetriever
from rag.vectorstore import PgVectorStore
logger = logging.getLogger(__name__)

from langchain_core.retrievers import BaseRetriever as LangChainBaseRetriever
from langchain_core.documents import Document as LangChainDocument
from langchain_core.callbacks import CallbackManagerForRetrieverRun


class VectorStoreRetriever(BaseRetriever):
    """
    Production-ready vector-based retriever for semantic search.
    
    Uses dense vector embeddings to find semantically similar documents.
    Better than keyword search for understanding meaning and context.
    
    Attributes:
        vector_store: Vector database instance
        embedding_model: Model for converting text to vectors
        search_type: Type of search ('similarity' or 'mmr')
        search_kwargs: Additional search parameters
    """
    
    def __init__(self,
                 vector_store: PgVectorStore,
                 embedding_model: EmbeddingModel,
                 search_type: str = "similarity",
                 search_kwargs: Dict[str, Any] = None):
        """
        Initialize vector store retriever.
        
        Args:
            vector_store: Vector database instance
            embedding_model: Embedding model instance
            search_type: Type of search ('similarity' or 'mmr')
            search_kwargs: Additional parameters (fetch_k, lambda_mult, etc.)
            
        Raises:
            ValueError: If inputs are invalid
        """
        super().__init__(name="VectorStoreRetriever")
        
        if vector_store is None:
            raise ValueError("Vector store cannot be None")
        if embedding_model is None:
            raise ValueError("Embedding model cannot be None")
        if search_type not in ['similarity', 'mmr']:
            raise ValueError("search_type must be 'similarity' or 'mmr'")
        
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.search_type = search_type
        self.search_kwargs = search_kwargs or {}
        
        logger.info(f"Initialized VectorStoreRetriever with {search_type} search")
    
    def _embed_query_with_retry(self, query: str, max_retries: int = 3) -> np.ndarray:
        """
        Embed query with retry logic for production reliability.
        
        Args:
            query: Query text to embed
            max_retries: Maximum number of retry attempts
            
        Returns:
            Query embedding vector
            
        Raises:
            RetrieverException: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                embedding = self.embedding_model.embed_query(query)
                
                # Validate embedding
                if embedding is None or len(embedding) == 0:
                    raise ValueError("Embedding model returned empty vector")
                
                return embedding
                
            except Exception as e:
                logger.warning(f"Embedding attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == max_retries - 1:
                    logger.error("All embedding attempts failed")
                    raise RetrieverException(f"Failed to embed query: {str(e)}")
                
                # Wait before retry (exponential backoff)
                import time
                time.sleep(2 ** attempt)
        
        raise RetrieverException("Unexpected error in embedding")
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
        """
        Retrieve semantically similar documents for the query.
        
        Args:
            query: Search query string
            top_k: Maximum number of documents to return
            
        Returns:
            List of semantically similar documents
            
        Raises:
            ValueError: If query is invalid
            RetrieverException: If retrieval fails
        """
        try:
            # Validate query
            self.validate_query(query)
            
            # Embed the query
            query_embedding = self._embed_query_with_retry(query)
            
            # Search vector store
            if self.search_type == "similarity":
                documents = self._similarity_search(query_embedding, top_k)
            elif self.search_type == "mmr":
                documents = self._mmr_search(query_embedding, top_k)
            else:
                raise ValueError(f"Unknown search type: {self.search_type}")
            
            # Log retrieval
            self.log_retrieval(query, len(documents))
            
            return documents
            
        except ValueError as ve:
            logger.error(f"Invalid query: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"Vector retrieval failed: {str(e)}")
            raise RetrieverException(f"Retrieval error: {str(e)}")
    
    def _similarity_search(self, query_embedding: np.ndarray, k: int) -> List[Document]:
        """
        Perform standard similarity search.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            
        Returns:
            List of similar documents
        """
        logger.info("::::: VECTOR STORE RETRIEVER:SIMILARITY SEARCH : BEGIN :::::")

        try:
            documents = self.vector_store.similarity_search(
                query_embedding=query_embedding,
                k=k
            )
            return documents
        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}")
            raise RetrieverException(f"Search failed: {str(e)}")
    
    def _mmr_search(self, query_embedding: np.ndarray, k: int) -> List[Document]:
        """
        Perform Maximal Marginal Relevance (MMR) search.
        
        MMR balances relevance with diversity to avoid redundant results.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            
        Returns:
            List of diverse, relevant documents
        """
        # Get more candidates than needed
        fetch_k = self.search_kwargs.get('fetch_k', k * 3)
        lambda_mult = self.search_kwargs.get('lambda_mult', 0.5)
        
        try:
            # Fetch initial candidates
            candidates = self.vector_store.similarity_search(
                query_embedding=query_embedding,
                k=fetch_k
            )
            
            if not candidates:
                return []
            
            # Apply MMR algorithm
            selected = []
            candidate_embeddings = [
                self.embedding_model.embed_query(doc.content)
                for doc in candidates
            ]
            
            while len(selected) < k and candidates:
                # Calculate MMR scores for remaining candidates
                mmr_scores = []
                for i, candidate in enumerate(candidates):
                    if candidate in selected:
                        continue
                    
                    # Relevance to query
                    relevance = self._cosine_similarity(
                        query_embedding, 
                        candidate_embeddings[i]
                    )
                    
                    # Maximum similarity to already selected documents
                    if selected:
                        selected_embeddings = [
                            self.embedding_model.embed_query(doc.content)
                            for doc in selected
                        ]
                        max_similarity = max(
                            self._cosine_similarity(candidate_embeddings[i], sel_emb)
                            for sel_emb in selected_embeddings
                        )
                    else:
                        max_similarity = 0.0
                    
                    # MMR score: balance relevance and diversity
                    mmr_score = lambda_mult * relevance - (1 - lambda_mult) * max_similarity
                    mmr_scores.append((candidate, mmr_score))
                
                # Select document with highest MMR score
                if mmr_scores:
                    best_doc, _ = max(mmr_scores, key=lambda x: x[1])
                    selected.append(best_doc)
                    candidates.remove(best_doc)
                else:
                    break
            
            return selected
            
        except Exception as e:
            logger.error(f"MMR search failed: {str(e)}")
            raise RetrieverException(f"MMR search failed: {str(e)}")
    
    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (0 to 1)
        """
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        
        if norm_product == 0:
            return 0.0
        
        return float(dot_product / norm_product)
    
    

    def as_langchain_retriever(self):
        """
        Wraps HybridRetriever into a LangChain compatible retriever.
        Required for MultiQueryRetriever.from_llm() to accept it.
        """
        
        # Local reference to self (HybridRetriever) for use inside inner class
        vector  = self

        # Inner class that extends LangChain's BaseRetriever
        class LangChainAdapter(LangChainBaseRetriever):

            def _get_relevant_documents(
                self, 
                query: str, 
                *, 
                run_manager: CallbackManagerForRetrieverRun  # required by LangChain
            ):
                # Call HybridRetriever's retrieve method
                docs = vector.retrieve(query)

                # Convert your Document objects to LangChain Document objects
                return [
                    LangChainDocument(
                        page_content=str(doc.content) if doc.content is not None else "",   # map content -> page_content
                        metadata=doc.metadata if isinstance(doc.metadata, dict) else {}    # ensure dict     
                       )
                    for doc in docs
                ]

        return LangChainAdapter()  # return instance of adapter