"""
ChromaDB implementation for lightweight embedded vector storage.
Suitable for development, testing, and small-to-medium production workloads.
"""

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from rag.exception.VectorStoreException import VectorStoreException
from typing import List, Optional, Dict, Any
import numpy as np
import os
from rag.vectorstore.BaseVectorStore import BaseVectorStore
from rag.vectorstore.DistanceMetric import DistanceMetric
import logging

# Configure logging for production monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChromaVectorStore(BaseVectorStore):
    """
    Production-ready ChromaDB implementation.
    
    Lightweight, embedded vector database suitable for:
    - Development and testing
    - Small to medium production workloads
    - Edge deployments
    
    Features:
    - Persistent storage to disk
    - Automatic embedding generation (optional)
    - Built-in metadata filtering
    
    Attributes:
        client: ChromaDB client instance
        collection: ChromaDB collection
        persist_directory: Directory for persistent storage
    """
    
    def __init__(self,
                 collection_name: str,
                 persist_directory: str = "./chroma_db",
                 distance_metric: DistanceMetric = DistanceMetric.COSINE,
                 embedding_function: Optional[Any] = None):
        """
        Initialize ChromaDB vector store with persistence.
        
        Args:
            collection_name: Name of the collection
            persist_directory: Directory to persist data
            distance_metric: Distance metric (cosine, euclidean, or dot_product)
            embedding_function: Optional custom embedding function
            
        Raises:
            VectorStoreException: If initialization fails
        """
        super().__init__(collection_name, distance_metric)
        
        self.persist_directory = persist_directory
        
        try:
            # Create persist directory if it doesn't exist
            os.makedirs(persist_directory, exist_ok=True)
            
            # Map distance metric to ChromaDB space
            space_mapping = {
                DistanceMetric.COSINE: "cosine",
                DistanceMetric.EUCLIDEAN: "l2",
                DistanceMetric.DOT_PRODUCT: "ip"
            }
            
            # Initialize ChromaDB client with persistence
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,  # Disable telemetry for production
                    allow_reset=False  # Prevent accidental data loss
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": space_mapping[distance_metric],
                    "description": f"Vector store for {collection_name}"
                },
                embedding_function=embedding_function
            )
            
            logger.info(
                f"ChromaVectorStore initialized: collection='{collection_name}', "
                f"persist_dir='{persist_directory}', metric={distance_metric.value}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaVectorStore: {str(e)}")
            raise VectorStoreException(f"Initialization failed: {str(e)}")
    
    def add_documents(self,
                     documents: List[Document],
                     embeddings: List[np.ndarray],
                     batch_size: int = 100) -> None:
        """
        Add documents with embeddings to ChromaDB.
        
        Args:
            documents: List of documents to add
            embeddings: Corresponding embedding vectors
            batch_size: Documents per batch (ChromaDB handles batching internally)
            
        Raises:
            ValueError: If documents and embeddings lengths don't match
            VectorStoreException: If addition fails
        """
        if len(documents) != len(embeddings):
            raise ValueError(
                f"Documents ({len(documents)}) and embeddings ({len(embeddings)}) "
                "length mismatch"
            )
        
        if not documents:
            logger.warning("No documents to add")
            return
        
        try:
            # Validate embeddings
            for emb in embeddings:
                self.validate_embedding(emb)
            
            # Prepare data in ChromaDB format
            ids = [doc.id for doc in documents]
            contents = [doc.content for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            embeddings_list = [emb.tolist() for emb in embeddings]
            
            # ChromaDB handles batching internally, but we can process in chunks
            # for better error handling and progress tracking
            total_added = 0
            for i in range(0, len(documents), batch_size):
                end_idx = min(i + batch_size, len(documents))
                
                # Use upsert to handle duplicate IDs (idempotent operation)
                self.collection.upsert(
                    ids=ids[i:end_idx],
                    documents=contents[i:end_idx],
                    metadatas=metadatas[i:end_idx],
                    embeddings=embeddings_list[i:end_idx]
                )
                
                total_added += (end_idx - i)
                logger.debug(f"Added batch: {total_added}/{len(documents)}")
            
            logger.info(f"Successfully added {total_added} documents to ChromaDB")
            
        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"Failed to add documents: {str(e)}")
            raise VectorStoreException(f"Document addition failed: {str(e)}")
    
    def similarity_search(self,
                         query_embedding: np.ndarray,
                         k: int = 5,
                         filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Search for similar documents with optional metadata filtering.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            filter: Optional metadata filters (ChromaDB where clause)
            
        Returns:
            List of similar documents with scores
            
        Raises:
            VectorStoreException: If search fails
        """
        try:
            # Validate query embedding
            self.validate_embedding(query_embedding)
            
            # Build query parameters
            query_params = {
                "query_embeddings": [query_embedding.tolist()],
                "n_results": k,
                "include": ["documents", "metadatas", "distances"]
            }
            
            # Add where clause for metadata filtering
            if filter:
                query_params["where"] = filter
            
            # Execute query
            results = self.collection.query(**query_params)
            
            # Convert to Document objects
            documents = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    # Convert distance to similarity score (1 - normalized distance)
                    distance = results['distances'][0][i]
                    similarity = 1.0 / (1.0 + distance)  # Convert distance to similarity
                    
                    doc = Document(
                        id=results['ids'][0][i],
                        content=results['documents'][0][i],
                        metadata=results['metadatas'][0][i] if results['metadatas'][0][i] else {},
                        score=similarity
                    )
                    documents.append(doc)
            
            logger.debug(f"ChromaDB search returned {len(documents)} results")
            
            return documents
            
        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}")
            raise VectorStoreException(f"Search failed: {str(e)}")
    
    def delete_documents(self, ids: List[str]) -> int:
        """
        Delete documents by IDs.
        
        Args:
            ids: List of document IDs to delete
            
        Returns:
            Number of documents deleted (ChromaDB doesn't return count)
            
        Raises:
            VectorStoreException: If deletion fails
        """
        if not ids:
            return 0
        
        try:
            # ChromaDB delete operation
            self.collection.delete(ids=ids)
            
            logger.info(f"Deleted {len(ids)} documents from ChromaDB")
            
            # ChromaDB doesn't return actual deletion count
            # Return requested count (assuming success)
            return len(ids)
            
        except Exception as e:
            logger.error(f"Document deletion failed: {str(e)}")
            raise VectorStoreException(f"Deletion failed: {str(e)}")
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """
        Retrieve single document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document if found, None otherwise
        """
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
            
            if results['ids']:
                return Document(
                    id=results['ids'][0],
                    content=results['documents'][0],
                    metadata=results['metadatas'][0] if results['metadatas'][0] else {}
                )
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {str(e)}")
            return None
    
    def count_documents(self) -> int:
        """
        Get total number of documents in the collection.
        
        Returns:
            Total document count
        """
        try:
            # ChromaDB count method
            count = self.collection.count()
            return count
        except Exception as e:
            logger.error(f"Failed to count documents: {str(e)}")
            return 0
    
    def clear(self) -> None:
        """
        Clear all documents from the collection.
        
        Warning: This operation cannot be undone!
        """
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata=self.collection.metadata
            )
            logger.warning(f"Cleared all documents from collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Failed to clear collection: {str(e)}")
            raise VectorStoreException(f"Clear operation failed: {str(e)}")