"""
Pinecone implementation for cloud-based serverless vector storage.
Ideal for production workloads requiring high scale and availability.
"""

from pinecone import Pinecone, ServerlessSpec, PodSpec
from typing import List, Optional, Dict, Any
import numpy as np
import time
from rag.exception.VectorStoreException import VectorStoreException
from rag.vectorstore.BaseVectorStore import BaseVectorStore
from rag.vectorstore.DistanceMetric import DistanceMetric
import logging

# Configure logging for production monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PineconeVectorStore(BaseVectorStore):
    """
    Production-ready Pinecone vector store implementation.
    
    Cloud-based, fully managed vector database suitable for:
    - High-scale production workloads
    - Global deployments
    - Serverless architectures
    
    Features:
    - Auto-scaling
    - High availability
    - Real-time updates
    - Built-in metadata filtering
    
    Attributes:
        pc: Pinecone client instance
        index: Pinecone index
        dimension: Embedding vector dimension
        namespace: Optional namespace for multi-tenancy
    """
    
    def __init__(self,
                 api_key: str,
                 index_name: str,
                 dimension: int = 1536,
                 distance_metric: DistanceMetric = DistanceMetric.COSINE,
                 cloud: str = "aws",
                 region: str = "us-east-1",
                 namespace: str = "",
                 serverless: bool = True):
        """
        Initialize Pinecone vector store.
        
        Args:
            api_key: Pinecone API key
            index_name: Name of the Pinecone index
            dimension: Embedding vector dimension
            distance_metric: Distance metric (cosine, euclidean, or dot_product)
            cloud: Cloud provider (aws, gcp, azure)
            region: Cloud region
            namespace: Optional namespace for data isolation
            serverless: Use serverless spec (True) or pod-based (False)
            
        Raises:
            VectorStoreException: If initialization fails
        """
        super().__init__(index_name, distance_metric)
        
        self.dimension = dimension
        self.namespace = namespace
        
        try:
            # Initialize Pinecone client
            self.pc = Pinecone(api_key=api_key)
            
            # Map distance metric to Pinecone metric
            metric_mapping = {
                DistanceMetric.COSINE: "cosine",
                DistanceMetric.EUCLIDEAN: "euclidean",
                DistanceMetric.DOT_PRODUCT: "dotproduct"
            }
            
            # Check if index exists
            existing_indexes = self.pc.list_indexes().names()
            
            if index_name not in existing_indexes:
                # Create new index
                logger.info(f"Creating new Pinecone index: {index_name}")
                
                if serverless:
                    # Serverless specification
                    spec = ServerlessSpec(
                        cloud=cloud,
                        region=region
                    )
                else:
                    # Pod-based specification (for dedicated resources)
                    spec = PodSpec(
                        environment=f"{cloud}-{region}",
                        pod_type="p1.x1"
                    )
                
                self.pc.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric=metric_mapping[distance_metric],
                    spec=spec
                )
                
                # Wait for index to be ready
                self._wait_for_index_ready(index_name)
            
            # Connect to index
            self.index = self.pc.Index(index_name)
            
            # Verify index dimensions match
            index_stats = self.index.describe_index_stats()
            logger.info(
                f"PineconeVectorStore initialized: index='{index_name}', "
                f"dim={dimension}, namespace='{namespace}', "
                f"total_vectors={index_stats.get('total_vector_count', 0)}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize PineconeVectorStore: {str(e)}")
            raise VectorStoreException(f"Initialization failed: {str(e)}")
    
    def _wait_for_index_ready(self, index_name: str, timeout: int = 300) -> None:
        """
        Wait for index to be ready after creation.
        
        Args:
            index_name: Name of the index
            timeout: Maximum wait time in seconds
            
        Raises:
            VectorStoreException: If index doesn't become ready in time
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                index_description = self.pc.describe_index(index_name)
                if index_description.status.get('ready'):
                    logger.info(f"Index {index_name} is ready")
                    return
            except Exception as e:
                logger.debug(f"Waiting for index: {str(e)}")
            
            time.sleep(5)
        
        raise VectorStoreException(f"Index {index_name} not ready after {timeout}s")
    
    def add_documents(self,
                     documents: List[Document],
                     embeddings: List[np.ndarray],
                     batch_size: int = 100) -> None:
        """
        Add documents with embeddings to Pinecone.
        
        Uses batching for optimal performance with Pinecone's API.
        
        Args:
            documents: List of documents to add
            embeddings: Corresponding embedding vectors
            batch_size: Documents per batch (max 100 for Pinecone)
            
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
        
        # Pinecone has max batch size of 100
        batch_size = min(batch_size, 100)
        
        try:
            # Validate embeddings
            for emb in embeddings:
                self.validate_embedding(emb, self.dimension)
            
            # Process in batches
            total_added = 0
            for i in range(0, len(documents), batch_size):
                end_idx = min(i + batch_size, len(documents))
                batch_docs = documents[i:end_idx]
                batch_embs = embeddings[i:end_idx]
                
                # Prepare vectors in Pinecone format
                vectors = []
                for doc, emb in zip(batch_docs, batch_embs):
                    vector = {
                        "id": doc.id,
                        "values": emb.tolist(),
                        "metadata": {
                            "content": doc.content,
                            **doc.metadata
                        }
                    }
                    vectors.append(vector)
                
                # Upsert to Pinecone (idempotent operation)
                self.index.upsert(
                    vectors=vectors,
                    namespace=self.namespace
                )
                
                total_added += len(vectors)
                logger.debug(f"Upserted batch: {total_added}/{len(documents)}")
            
            logger.info(f"Successfully added {total_added} documents to Pinecone")
            
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
            filter: Optional metadata filters (Pinecone filter dict)
            
        Returns:
            List of similar documents with scores
            
        Raises:
            VectorStoreException: If search fails
        """
        try:
            # Validate query embedding
            self.validate_embedding(query_embedding, self.dimension)
            
            # Build query parameters
            query_params = {
                "vector": query_embedding.tolist(),
                "top_k": k,
                "namespace": self.namespace,
                "include_metadata": True
            }
            
            # Add filter if provided
            if filter:
                query_params["filter"] = filter
            
            # Execute query
            results = self.index.query(**query_params)
            
            # Convert to Document objects
            documents = []
            for match in results.get('matches', []):
                metadata = match.get('metadata', {}).copy()
                
                # Extract content from metadata
                content = metadata.pop('content', '')
                
                doc = Document(
                    id=match['id'],
                    content=content,
                    metadata=metadata,
                    score=match.get('score', 0.0)
                )
                documents.append(doc)
            
            logger.debug(f"Pinecone search returned {len(documents)} results")
            
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
            Number of documents deleted (same as input length)
            
        Raises:
            VectorStoreException: If deletion fails
        """
        if not ids:
            return 0
        
        try:
            # Pinecone delete operation
            self.index.delete(
                ids=ids,
                namespace=self.namespace
            )
            
            logger.info(f"Deleted {len(ids)} documents from Pinecone")
            
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
            results = self.index.fetch(
                ids=[doc_id],
                namespace=self.namespace
            )
            
            if doc_id in results.get('vectors', {}):
                vector_data = results['vectors'][doc_id]
                metadata = vector_data.get('metadata', {}).copy()
                content = metadata.pop('content', '')
                
                return Document(
                    id=doc_id,
                    content=content,
                    metadata=metadata
                )
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {str(e)}")
            return None
    
    def count_documents(self) -> int:
        """
        Get total number of documents in the namespace.
        
        Returns:
            Total document count
        """
        try:
            stats = self.index.describe_index_stats()
            
            if self.namespace:
                # Get count for specific namespace
                namespace_stats = stats.get('namespaces', {}).get(self.namespace, {})
                count = namespace_stats.get('vector_count', 0)
            else:
                # Get total count across all namespaces
                count = stats.get('total_vector_count', 0)
            
            return count
        except Exception as e:
            logger.error(f"Failed to count documents: {str(e)}")
            return 0
    
    def clear_namespace(self) -> None:
        """
        Clear all documents from the current namespace.
        
        Warning: This operation cannot be undone!
        """
        try:
            self.index.delete(delete_all=True, namespace=self.namespace)
            logger.warning(f"Cleared all documents from namespace '{self.namespace}'")
        except Exception as e:
            logger.error(f"Failed to clear namespace: {str(e)}")
            raise VectorStoreException(f"Clear operation failed: {str(e)}")