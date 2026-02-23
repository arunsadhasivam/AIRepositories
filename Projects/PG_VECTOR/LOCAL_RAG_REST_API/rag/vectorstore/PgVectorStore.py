"""
PostgreSQL with pgvector extension implementation.
Production-ready vector store using reliable PostgreSQL database.
"""

import psycopg2
from psycopg2 import pool, extras
from psycopg2.extensions import register_adapter, AsIs
import json
from contextlib import contextmanager
from typing import List, Optional, Dict, Any
import numpy as np
from rag.vectorstore.BaseVectorStore import BaseVectorStore
from rag.vectorstore.DistanceMetric import DistanceMetric
import logging

# Configure logging for production monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Register numpy array adapter for PostgreSQL
def adapt_numpy_array(arr):
    """Adapter to convert numpy array to PostgreSQL array format."""
    return AsIs(f"'[{','.join(map(str, arr.tolist()))}]'")

register_adapter(np.ndarray, adapt_numpy_array)


class PgVectorStore(BaseVectorStore):
    """
    Production-ready PostgreSQL + pgvector implementation.
    
    Uses connection pooling, batching, and proper error handling.
    Suitable for production workloads with millions of vectors.
    
    Attributes:
        connection_pool: Database connection pool
        table_name: Name of the table storing vectors
        dimension: Embedding vector dimension
    """
    
    def __init__(self,
                 connection_string: str,
                 collection_name: str,
                 dimension: int = 1536,
                 distance_metric: DistanceMetric = DistanceMetric.COSINE,
                 pool_size: int = 10,
                 max_overflow: int = 20):
        """
        Initialize PostgreSQL vector store with connection pooling.
        
        Args:
            connection_string: PostgreSQL connection string
            collection_name: Table name for this collection
            dimension: Embedding vector dimension
            distance_metric: Distance metric to use
            pool_size: Number of connections in pool
            max_overflow: Maximum overflow connections
            
        Raises:
            VectorStoreException: If initialization fails
        """
        super().__init__(collection_name, distance_metric)
        
        self.dimension = dimension
        self.table_name = f"vectors_{collection_name}"
        
        try:
            # Create connection pool for production use
            self.connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=pool_size + max_overflow,
                dsn=connection_string
            )
            
            # Initialize database schema
            self._initialize_database()
            
            logger.info(
                f"PgVectorStore initialized: table='{self.table_name}', "
                f"dim={dimension}, metric={distance_metric.value}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize PgVectorStore: {str(e)}")
            raise VectorStoreException(f"Initialization failed: {str(e)}")
    
    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections from pool.
        
        Yields:
            Database connection
            
        Ensures proper connection return to pool.
        """
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def _initialize_database(self) -> None:
        """
        Initialize database schema and indexes.
        
        Creates:
        - Table with proper columns
        - Vector similarity index (IVFFlat or HNSW)
        - Metadata JSONB index
        
        Raises:
            VectorStoreException: If schema creation fails
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Enable pgvector extension
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    
                    # Create table with proper schema
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.table_name} (
                            id TEXT PRIMARY KEY,
                            content TEXT NOT NULL,
                            metadata JSONB DEFAULT '{{}}'::jsonb,
                            embedding vector({self.dimension}),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Determine distance operator based on metric
                    if self.distance_metric == DistanceMetric.COSINE:
                        ops = "vector_cosine_ops"
                    elif self.distance_metric == DistanceMetric.EUCLIDEAN:
                        ops = "vector_l2_ops"
                    else:  # DOT_PRODUCT
                        ops = "vector_ip_ops"
                    
                    # Create IVFFlat index for fast similarity search
                    # For production, consider HNSW index for better recall
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx
                        ON {self.table_name}
                        USING ivfflat (embedding {ops})
                        WITH (lists = 100)
                    """)
                    
                    # Create JSONB index for metadata filtering
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_metadata_idx
                        ON {self.table_name}
                        USING gin (metadata)
                    """)
                    
                    # Create index on created_at for time-based queries
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_created_at_idx
                        ON {self.table_name} (created_at DESC)
                    """)
                    
                    conn.commit()
                    
                    logger.info(f"Database schema initialized for {self.table_name}")
                    
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise VectorStoreException(f"Schema creation failed: {str(e)}")
    
    def add_documents(self,
                     documents: List[Document],
                     embeddings: List[np.ndarray],
                     batch_size: int = 100) -> None:
        """
        Add documents with embeddings in batches for efficiency.
        
        Uses UPSERT (INSERT ... ON CONFLICT) for idempotency.
        
        Args:
            documents: List of documents to add
            embeddings: Corresponding embedding vectors
            batch_size: Documents per batch (default: 100)
            
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
            for i, emb in enumerate(embeddings):
                self.validate_embedding(emb, self.dimension)
            
            # Process in batches
            total_added = 0
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i + batch_size]
                batch_embs = embeddings[i:i + batch_size]
                
                self._add_batch(batch_docs, batch_embs)
                total_added += len(batch_docs)
                
                logger.debug(f"Added batch {i//batch_size + 1}: {total_added}/{len(documents)}")
            
            logger.info(f"Successfully added {total_added} documents to {self.table_name}")
            
        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"Failed to add documents: {str(e)}")
            raise VectorStoreException(f"Document addition failed: {str(e)}")
    
    def _add_batch(self, documents: List[Document], embeddings: List[np.ndarray]) -> None:
        """
        Add a single batch of documents to database.
        
        Args:
            documents: Batch of documents
            embeddings: Batch of embeddings
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Prepare batch data
                batch_data = [
                    (
                        doc.id,
                        doc.content,
                        json.dumps(doc.metadata),
                        emb.tolist()
                    )
                    for doc, emb in zip(documents, embeddings)
                ]
                
                # Use execute_values for efficient batch insert
                extras.execute_values(
                    cur,
                    f"""
                    INSERT INTO {self.table_name} (id, content, metadata, embedding)
                    VALUES %s
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    batch_data,
                    template="(%s, %s, %s::jsonb, %s::vector)"
                )
                
                conn.commit()
    
    def similarity_search(self,
                         query_embedding: np.ndarray,
                         k: int = 5,
                         filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Search for similar documents with optional metadata filtering.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            filter: Optional metadata filters (e.g., {"category": "tech"})
            
        Returns:
            List of similar documents with scores
            
        Raises:
            VectorStoreException: If search fails
        """
        try:
            # Validate query embedding
            self.validate_embedding(query_embedding, self.dimension)
            
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                    # Determine distance operator
                    if self.distance_metric == DistanceMetric.COSINE:
                        distance_op = "<=>"
                    elif self.distance_metric == DistanceMetric.EUCLIDEAN:
                        distance_op = "<->"
                    else:  # DOT_PRODUCT
                        distance_op = "<#>"
                    
                    # Build query with optional filtering
                    query = f"""
                        SELECT 
                            id, 
                            content, 
                            metadata,
                            embedding {distance_op} %s::vector AS distance
                        FROM {self.table_name}
                    """
                    
                    params = [query_embedding.tolist()]
                    
                    # Add metadata filter if provided
                    if filter:
                        filter_conditions = []
                        for key, value in filter.items():
                            filter_conditions.append(f"metadata @> %s::jsonb")
                            params.append(json.dumps({key: value}))
                        
                        if filter_conditions:
                            query += " WHERE " + " AND ".join(filter_conditions)
                    
                    # Order by distance and limit
                    query += f" ORDER BY distance ASC LIMIT %s"
                    params.append(k)
                    
                    # Execute query
                    cur.execute(query, params)
                    results = cur.fetchall()
                    
                    # Convert to Document objects
                    documents = []
                    for row in results:
                        doc = Document(
                            id=row['id'],
                            content=row['content'],
                            metadata=row['metadata'],
                            score=1.0 - float(row['distance'])  # Convert distance to similarity
                        )
                        documents.append(doc)
                    
                    logger.debug(f"Similarity search returned {len(documents)} results")
                    
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
            Number of documents deleted
            
        Raises:
            VectorStoreException: If deletion fails
        """
        if not ids:
            return 0
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"DELETE FROM {self.table_name} WHERE id = ANY(%s)",
                        (ids,)
                    )
                    deleted_count = cur.rowcount
                    conn.commit()
                    
                    logger.info(f"Deleted {deleted_count} documents from {self.table_name}")
                    
                    return deleted_count
                    
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
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                    cur.execute(
                        f"SELECT id, content, metadata FROM {self.table_name} WHERE id = %s",
                        (doc_id,)
                    )
                    row = cur.fetchone()
                    
                    if row:
                        return Document(
                            id=row['id'],
                            content=row['content'],
                            metadata=row['metadata']
                        )
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {str(e)}")
            return None
    
    def count_documents(self) -> int:
        """
        Get total number of documents in the store.
        
        Returns:
            Total document count
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                    count = cur.fetchone()[0]
                    return count
        except Exception as e:
            logger.error(f"Failed to count documents: {str(e)}")
            return 0
    
    def close(self) -> None:
        """Close all connections in the pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Closed all database connections")