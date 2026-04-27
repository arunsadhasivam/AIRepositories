"""
Hybrid retriever combining dense and sparse retrieval methods.
Provides best of both worlds: semantic understanding + keyword precision.
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
from rag.retriever.BaseRetriever import BaseRetriever
from rag.retriever.config.RetrieverConfig import RetrieverConfig
from rag.exception.RetrieverException import RetrieverException
from langchain_core.retrievers import BaseRetriever as LangChainBaseRetriever
from langchain_core.documents import Document as LangChainDocument
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from rag.retriever.Document import Document
import logging


# Configure logging for production monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """
    Production-ready hybrid retriever combining multiple retrieval strategies.
    
    Combines dense vector search (semantic) with sparse keyword search (BM25)
    to leverage both semantic understanding and exact keyword matching.
    
    Uses Reciprocal Rank Fusion (RRF) for score combination.
    
    Attributes:
        vector_retriever: Dense vector-based retriever
        sparse_retriever: Sparse keyword-based retriever (BM25)
        config: Retriever configuration
    """
    
    def __init__(self,
                 vector_retriever: BaseRetriever,
                 sparse_retriever: BaseRetriever,
                 config: RetrieverConfig = None):
        """
        Initialize hybrid retriever with two retrieval strategies.
        
        Args:
            vector_retriever: Semantic vector-based retriever
            sparse_retriever: Keyword-based sparse retriever
            config: Configuration for weights and parameters
            
        Raises:
            ValueError: If retrievers are invalid
        """
        super().__init__(name="HybridRetriever")
        
        if vector_retriever is None:
            raise ValueError("vector_retriever cannot be None")
        if sparse_retriever is None:
            raise ValueError("sparse_retriever cannot be None")
        
        self.vector_retriever = vector_retriever
        self.sparse_retriever = sparse_retriever
        self.config = config or RetrieverConfig()
        
        logger.info(
            f"Initialized HybridRetriever with weights: "
            f"vector={self.config.vector_weight}, sparse={self.config.sparse_weight}"
        )
    
    def retrieve(self, query: str, top_k: int = 10) -> List[Document]:
        """
        Retrieve documents using hybrid approach.
        
        Combines results from both vector and sparse retrievers using
        Reciprocal Rank Fusion (RRF) algorithm for optimal ranking.
        
        Args:
            query: Search query string
            top_k: Maximum number of documents to return
            
        Returns:
            List of documents ranked by combined relevance
            
        Raises:
            ValueError: If query is invalid
            RetrieverException: If retrieval fails
        """
        logging.info(f"-----------------------RAG.HYBRID.RETRIEVER BEGIN--------------------------------------")

        try:
            if self.config.top_k:
                top_k  = int(self.config.top_k) # *2 if want more  
            # Validate query
            self.validate_query(query)
            fetch_k = max(top_k, 1)
            logging.info(f'::::: HYBRID RETRIEVER ::: VECTOR RETRIEVER::::query={query}, top-k={fetch_k}')    
            vector_results = self._safe_retrieve(
                self.vector_retriever, 
                query, 
                fetch_k, 
                "vector"
            )
            
            logging.info(f'::::: HYBRID RETRIEVER ::: SOLR SPARSE RETRIEVER::::query={query}, top-k={fetch_k}')    
            sparse_results = self._safe_retrieve(
                self.sparse_retriever, 
                query, 
                fetch_k, 
                "sparse"
            )
            
            # Combine results using Reciprocal Rank Fusion
            combined_results = self._reciprocal_rank_fusion(
                vector_results, 
                sparse_results
            )

            vector_len = len(sparse_results)
            sparse_solr_len = len(sparse_results)
            totlen = vector_len + sparse_solr_len
            logging.info(f'::::: HYBRID RETRIEVER ::: (SOLR SPARSE + VECTOR) COMBINED::::VECTOR Result={vector_len}, SPARSE SOLR RESULT={sparse_solr_len}, total={totlen}')    

            
            # Apply score threshold if configured
            if self.config.min_score_threshold > 0:
                combined_results = [
                    (doc, score) for doc, score in combined_results
                    if score >= self.config.min_score_threshold
                ]
            
            # Take top K
            top_results = combined_results[:top_k]
            
            # Extract documents
            final_docs = [doc for doc, _ in top_results]
            
            # Log retrieval statistics
            self._log_retrieval_stats(
                query, 
                len(vector_results), 
                len(sparse_results), 
                len(final_docs)
            )
            logging.info(f"-----------------------RAG.HYBRID.RETRIEVER END--------------------------------------\n")

            return final_docs
            
        except ValueError as ve:
            logger.error(f"Invalid query: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"Hybrid retrieval failed: {str(e)}")
            raise RetrieverException(f"Hybrid retrieval error: {str(e)}")

    def _safe_retrieve(self, 
                       retriever: BaseRetriever, 
                       query: str, 
                       k: int,
                       retriever_name: str) -> List[Document]:
        """
        Safely retrieve from a retriever with error handling.
        
        Args:
            retriever: Retriever instance to use
            query: Search query
            k: Number of results
            retriever_name: Name for logging
            
        Returns:
            List of documents (empty if retrieval fails)
        """
        try:
            results = retriever.retrieve(query, top_k=k)
            logger.debug(f"{retriever_name} retriever returned {len(results)} results")
            return results
        except Exception as e:
            logger.warning(f"{retriever_name} retriever failed: {str(e)}")
            return []  # Return empty list on failure, don't crash entire retrieval
    
    def _reciprocal_rank_fusion(self,
                                vector_results: List[Document],
                                sparse_results: List[Document],
                                k: int = 60) -> List[Tuple[Document, float]]:
        """
        Combine results using Reciprocal Rank Fusion (RRF) algorithm.
        
        RRF formula: score = sum(weight_i / (k + rank_i))
        where k is a constant (typically 60) to reduce impact of high ranks.
        
        Args:
            vector_results: Results from vector retriever
            sparse_results: Results from sparse retriever
            k: RRF constant (default: 60)
            
        Returns:
            List of (document, score) tuples sorted by combined score
        """
        # Track all documents and their scores
        doc_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}
        
        # Process vector results
        for rank, doc in enumerate(vector_results, start=1):
            # RRF score with weighting
            score = self.config.vector_weight / (k + rank)
            
            if doc.id in doc_scores:
                doc_scores[doc.id] += score
            else:
                doc_scores[doc.id] = score
                doc_map[doc.id] = doc
        
        # Process sparse results
        for rank, doc in enumerate(sparse_results, start=1):
            # RRF score with weighting
            score = self.config.sparse_weight / (k + rank)
            
            if doc.id in doc_scores:
                doc_scores[doc.id] += score
            else:
                doc_scores[doc.id] = score
                doc_map[doc.id] = doc
        
        # Normalize scores if configured
        if self.config.normalize_scores and doc_scores:
            max_score = max(doc_scores.values())
            if max_score > 0:
                doc_scores = {
                    doc_id: score / max_score 
                    for doc_id, score in doc_scores.items()
                }
        
        # Sort by score descending
        sorted_docs = sorted(
            doc_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Create result list with updated scores
        results = []
        for doc_id, score in sorted_docs:
            doc = doc_map[doc_id]
            # Create new document with updated score
            doc_with_score = Document(
                id=doc.id,
                content=doc.content,
                metadata=doc.metadata.copy(),
                score=score
            )
            results.append((doc_with_score, score))
        
        return results
    
    def _log_retrieval_stats(self, 
                            query: str, 
                            vector_count: int, 
                            sparse_count: int, 
                            final_count: int) -> None:
        """
        Log detailed retrieval statistics for monitoring.
        
        Args:
            query: The query that was executed
            vector_count: Number of vector results
            sparse_count: Number of sparse results
            final_count: Number of final combined results
        """
        logger.info(
            f"[HybridRetriever] Query: '{query[:50]}...', "
            f"Vector: {vector_count}, Sparse: {sparse_count}, "
            f"Final: {final_count}"
        )
    
    def update_weights(self, vector_weight: float, sparse_weight: float) -> None:
        """
        Update retriever weights dynamically.
        
        Useful for A/B testing or adaptive retrieval strategies.
        
        Args:
            vector_weight: New weight for vector retriever
            sparse_weight: New weight for sparse retriever
        """
        if not 0 <= vector_weight <= 1:
            raise ValueError("vector_weight must be between 0 and 1")
        if not 0 <= sparse_weight <= 1:
            raise ValueError("sparse_weight must be between 0 and 1")
        
        self.config.vector_weight = vector_weight
        self.config.sparse_weight = sparse_weight
        
        logger.info(f"Updated weights: vector={vector_weight}, sparse={sparse_weight}")

    def as_langchain_retriever(self):
        """
        Wraps HybridRetriever into a LangChain compatible retriever.
        Required for MultiQueryRetriever.from_llm() to accept it.
        """
        
        # Local reference to self (HybridRetriever) for use inside inner class
        hybrid = self

        # Inner class that extends LangChain's BaseRetriever
        class LangChainAdapter(LangChainBaseRetriever):

            def _get_relevant_documents(
                self, 
                query: str, 
                *, 
                run_manager: CallbackManagerForRetrieverRun  # required by LangChain
            ):
                # Call HybridRetriever's retrieve method
                docs = hybrid.retrieve(query)

                # Convert your Document objects to LangChain Document objects
                return [
                    LangChainDocument(
                        page_content=str(doc.content) if doc.content is not None else "",   # map content -> page_content
                        metadata=doc.metadata if isinstance(doc.metadata, dict) else {}    # ensure dict     
                       )
                    for doc in docs
                ]

        return LangChainAdapter()  # return instance of adapter