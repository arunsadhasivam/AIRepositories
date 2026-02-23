"""
BM25 Retriever implementation using Okapi BM25 algorithm.
Provides keyword-based sparse retrieval with TF-IDF weighting.
"""

from collections import Counter, defaultdict
import math
import re
from typing import List, Dict, Set
import numpy as np
from rag.retriever.BaseRetriever import BaseRetriever
from rag.retriever.Document import Document
import logging
from rag.exception.RetrieverException import RetrieverException

logger = logging.getLogger(__name__)


class BM25Retriever(BaseRetriever):
    """
    Production-ready BM25 retriever for keyword-based search.
    
    Uses the Okapi BM25 ranking function to score documents based on
    term frequency and inverse document frequency. Suitable for
    exact keyword matching and traditional information retrieval.
    
    Attributes:
        documents: Corpus of all searchable documents
        k1: Term frequency saturation parameter (default: 1.5)
        b: Length normalization parameter (default: 0.75)
        epsilon: Small value to prevent division by zero
    """
    
    def __init__(self, 
                 documents: List[Document],
                 k1: float = 1.5,
                 b: float = 0.75,
                 use_stemming: bool = False):
        """
        Initialize BM25 retriever with document corpus.
        
        Args:
            documents: List of documents to index
            k1: Controls term frequency saturation (1.2-2.0 typical)
            b: Controls document length normalization (0.75 typical)
            use_stemming: Whether to apply word stemming (requires nltk)
            
        Raises:
            ValueError: If documents list is empty or parameters invalid
        """
        super().__init__(name="BM25Retriever")
        
        # Validate inputs
        if not documents:
            raise ValueError("Document list cannot be empty")
        if not 0 <= b <= 1:
            raise ValueError("Parameter b must be between 0 and 1")
        if k1 <= 0:
            raise ValueError("Parameter k1 must be positive")
        
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.epsilon = 1e-10
        self.use_stemming = use_stemming
        
        # Index structures
        self.term_frequencies: Dict[str, Dict[str, float]] = {}  # doc_id -> {term: freq}
        self.document_frequencies: Dict[str, int] = defaultdict(int)  # term -> doc count
        self.document_lengths: Dict[str, int] = {}  # doc_id -> length
        self.avg_doc_length: float = 0.0
        self.vocabulary: Set[str] = set()
        
        # Build index on initialization
        try:
            self._build_index()
            logger.info(f"BM25 index built with {len(documents)} documents, "
                       f"{len(self.vocabulary)} unique terms")
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {str(e)}")
            raise RetrieverException(f"Index construction failed: {str(e)}")
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into individual terms.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of normalized tokens
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters, keep only alphanumeric and spaces
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Split on whitespace
        tokens = text.split()
        
        # Remove very short tokens (likely not meaningful)
        tokens = [t for t in tokens if len(t) > 1]
        
        # Apply stemming if enabled
        if self.use_stemming:
            try:
                from nltk.stem import PorterStemmer
                stemmer = PorterStemmer()
                tokens = [stemmer.stem(token) for token in tokens]
            except ImportError:
                logger.warning("NLTK not available, skipping stemming")
        
        return tokens
    
    def _build_index(self) -> None:
        """
        Build inverted index for BM25 scoring.
        
        Creates data structures for efficient retrieval:
        - Term frequencies per document
        - Document frequencies per term
        - Document lengths
        - Average document length
        """
        total_length = 0
        
        # Process each document
        for doc in self.documents:
            # Tokenize document content
            tokens = self._tokenize(doc.content)
            
            if not tokens:
                logger.warning(f"Document {doc.id} has no valid tokens")
                continue
            
            # Calculate term frequencies for this document
            term_freq = Counter(tokens)
            self.term_frequencies[doc.id] = dict(term_freq)
            
            # Update vocabulary
            self.vocabulary.update(term_freq.keys())
            
            # Track document length
            doc_length = len(tokens)
            self.document_lengths[doc.id] = doc_length
            total_length += doc_length
            
            # Update document frequencies (how many docs contain each term)
            for term in term_freq.keys():
                self.document_frequencies[term] += 1
        
        # Calculate average document length
        if self.documents:
            self.avg_doc_length = total_length / len(self.documents)
        else:
            self.avg_doc_length = 0.0
    
    def _calculate_idf(self, term: str) -> float:
        """
        Calculate Inverse Document Frequency for a term.
        
        IDF measures how rare/common a term is across all documents.
        Rare terms get higher weights.
        
        Args:
            term: Term to calculate IDF for
            
        Returns:
            IDF score for the term
        """
        # Get number of documents containing this term
        df = self.document_frequencies.get(term, 0)
        
        if df == 0:
            return 0.0
        
        # Total number of documents
        N = len(self.documents)
        
        # BM25 IDF formula: log((N - df + 0.5) / (df + 0.5) + 1)
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
        
        return idf
    
    def _calculate_bm25_score(self, doc: Document, query_terms: List[str]) -> float:
        """
        Calculate BM25 relevance score for a document given query terms.
        
        BM25 combines:
        - Term frequency (how often query terms appear in doc)
        - Inverse document frequency (how rare the terms are)
        - Document length normalization
        
        Args:
            doc: Document to score
            query_terms: List of query terms
            
        Returns:
            BM25 relevance score (higher = more relevant)
        """
        score = 0.0
        
        # Get precomputed data for this document
        doc_tf = self.term_frequencies.get(doc.id, {})
        doc_length = self.document_lengths.get(doc.id, 0)
        
        # Avoid division by zero
        if doc_length == 0:
            return 0.0
        
        # Calculate length normalization factor
        length_norm = (1 - self.b) + self.b * (doc_length / (self.avg_doc_length + self.epsilon))
        
        # Score each query term
        for term in query_terms:
            # Get term frequency in document
            tf = doc_tf.get(term, 0)
            
            if tf == 0:
                continue  # Term not in document
            
            # Calculate IDF
            idf = self._calculate_idf(term)
            
            # BM25 formula: IDF * (tf * (k1 + 1)) / (tf + k1 * length_norm)
            term_score = idf * (tf * (self.k1 + 1)) / (tf + self.k1 * length_norm)
            score += term_score
        
        return score
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
        """
        Retrieve most relevant documents for the given query.
        
        Args:
            query: Search query string
            top_k: Maximum number of documents to return
            
        Returns:
            List of documents ordered by relevance (highest first)
            
        Raises:
            ValueError: If query is invalid
            RetrieverException: If retrieval fails
        """
        try:
            # Validate query
            self.validate_query(query)
            
            # Tokenize query
            query_terms = self._tokenize(query)
            
            if not query_terms:
                logger.warning("Query produced no valid terms")
                return []
            
            # Score all documents
            doc_scores = []
            for doc in self.documents:
                score = self._calculate_bm25_score(doc, query_terms)
                
                if score > 0:  # Only include documents with positive scores
                    # Create a copy of the document with score
                    doc_with_score = Document(
                        id=doc.id,
                        content=doc.content,
                        metadata=doc.metadata.copy(),
                        score=score
                    )
                    doc_scores.append((doc_with_score, score))
            
            # Sort by score descending
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Take top K
            top_docs = [doc for doc, _ in doc_scores[:top_k]]
            
            # Log retrieval
            self.log_retrieval(query, len(top_docs))
            
            return top_docs
            
        except ValueError as ve:
            logger.error(f"Invalid query: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"BM25 retrieval failed: {str(e)}")
            raise RetrieverException(f"Retrieval error: {str(e)}")
    
    def add_documents(self, new_documents: List[Document]) -> None:
        """
        Add new documents to the index (incremental indexing).
        
        Args:
            new_documents: List of documents to add
        """
        if not new_documents:
            return
        
        try:
            # Add to document list
            self.documents.extend(new_documents)
            
            # Rebuild index (in production, consider incremental updates)
            self._build_index()
            
            logger.info(f"Added {len(new_documents)} documents to BM25 index")
            
        except Exception as e:
            logger.error(f"Failed to add documents: {str(e)}")
            raise RetrieverException(f"Document addition failed: {str(e)}")