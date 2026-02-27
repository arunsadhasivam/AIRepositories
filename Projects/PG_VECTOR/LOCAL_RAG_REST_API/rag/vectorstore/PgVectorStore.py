"""
PostgreSQL with pgvector extension implementation.
Production-ready vector store using reliable PostgreSQL database.
Includes RLS (Row Level Security) support - no LangChain dependency.
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
from rag.exception.VectorStoreException import VectorStoreException
from rag.retriever.Document import Document
import logging

# Configure logging for production monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# In-memory cache: tracks which collections have RLS already enabled
# Avoids repeated ALTER TABLE calls across multiple instances
_rls_enabled_cache = set()

# Register numpy array adapter so numpy arrays can be passed directly to psycopg2
def adapt_numpy_array(arr):
    """Adapter to convert numpy array to PostgreSQL vector format."""
    return AsIs(f"'[{','.join(map(str, arr.tolist()))}]'")

register_adapter(np.ndarray, adapt_numpy_array)


class PgVectorStore(BaseVectorStore):
    """
    Production-ready PostgreSQL + pgvector implementation with RLS support.

    No LangChain dependency - pure psycopg2 implementation.
    Uses connection pooling, batching, RLS enforcement, and proper error handling.
    Suitable for production workloads with millions of vectors.

    Attributes:
        connection_pool : Database connection pool
        table_name      : Name of the table storing vectors
        dimension       : Embedding vector dimension
        user_role       : DB user role (used to grant RLS permissions)
    """

    def __init__(self,
                 connection_string: str,
                 connection_string_admin: str,
                 collection_name: str,
                 dimension: int = 1536,
                 distance_metric: DistanceMetric = DistanceMetric.COSINE,
                 pool_size: int = 10,
                 max_overflow: int = 20,
                 user_role: Optional[str] = None,
                 enable_rls: bool = False):
        """
        Initialize PostgreSQL vector store with connection pooling and optional RLS.

        Args:
            connection_string : psycopg2 DSN string e.g. "host=.. dbname=.. user=.. password=.."
            collection_name   : Table name for this collection
            dimension         : Embedding vector dimension (default: 1536)
            distance_metric   : Distance metric to use (COSINE/EUCLIDEAN/DOT_PRODUCT)
            pool_size         : Number of connections in pool (default: 10)
            max_overflow      : Maximum overflow connections (default: 20)
            user_role         : DB role to grant RLS permissions to (required if enable_rls=True)
            enable_rls        : Whether to enable Row Level Security on the table

        Raises:
            VectorStoreException: If initialization fails
        """
        # Call parent constructor with collection name and distance metric
        super().__init__(collection_name, distance_metric)

        # Store dimension for validation later
        self.dimension = dimension

        # Sanitize table name: replace hyphens with underscores (valid SQL identifier)
        self.table_name = f"{collection_name.replace('-', '_')}"

        # Store user role for RLS grant statements
        self.user_role = user_role

        # Store whether RLS should be enabled
        self.enable_rls = enable_rls

        self.connection_string_admin = connection_string_admin
        try:
            # Create a thread-safe connection pool for concurrent requests
            self.connection_pool = pool.ThreadedConnectionPool(
                minconn=1,                          # Always keep at least 1 connection open
                maxconn=pool_size + max_overflow,   # Max total connections allowed
                dsn=connection_string               # psycopg2 DSN string
            )

            self.connection_admin_pool = pool.ThreadedConnectionPool(
                minconn=1,                          # Always keep at least 1 connection open
                maxconn=pool_size + max_overflow,   # Max total connections allowed
                dsn=connection_string_admin               # psycopg2 DSN string
            )

            # Create the table, indexes, and optionally enable RLS
            self._initialize_database()

            logger.info(
                f"PgVectorStore initialized: table='{self.table_name}', "
                f"dim={dimension}, metric={distance_metric.value}, rls={enable_rls}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize PgVectorStore: {str(e)}")
            raise VectorStoreException(f"Initialization failed: {str(e)}")

    @contextmanager
    def _get_connection(self):
        """
        Context manager that borrows a connection from the pool and returns it after use.

        Yields:
            psycopg2 connection object

        Ensures the connection is always returned to the pool (even on exception).
        """
        conn = None
        try:
            # Borrow a connection from the pool
            conn = self.connection_pool.getconn()
            yield conn
        finally:
            # Always return connection to pool, even if an error occurred
            if conn:
                self.connection_pool.putconn(conn)

    @contextmanager
    def _get_admin_connection(self):
        """
        Context manager that borrows a connection from the pool and returns it after use.

        Yields:
            psycopg2 connection object

        Ensures the connection is always returned to the pool (even on exception).
        """
        conn = None
        try:
            # Borrow a connection from the pool
            conn = self.connection_admin_pool.getconn()
            yield conn
        finally:
            # Always return connection to pool, even if an error occurred
            if conn:
                self.connection_admin_pool.putconn(conn)

    def _initialize_database(self) -> None:
        """
        Initialize database schema, indexes, and optionally RLS.

        Creates:
          - pgvector extension
          - Table with id, content, metadata, embedding, timestamps
          - IVFFlat index for fast vector similarity search
          - GIN index on metadata JSONB for filtered search
          - Index on created_at for time-based queries
          - Optionally: RLS policies via _ensure_rls_enabled()

        Raises:
            VectorStoreException: If schema creation fails
        """
        try:
            with self._get_admin_connection() as conn:
                with conn.cursor() as cur:

                    # Enable pgvector extension (idempotent - safe to run multiple times)
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

                    # Create the main documents table if it doesn't already exist
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.table_name} (
                            id          TEXT PRIMARY KEY,
                            content     TEXT NOT NULL,
                            metadata    JSONB DEFAULT '{{}}'::jsonb,
                            embedding   vector({self.dimension}),
                            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Choose the correct index operator class based on distance metric
                    if self.distance_metric == DistanceMetric.COSINE:
                        ops = "vector_cosine_ops"    # Cosine similarity (<=>)
                    elif self.distance_metric == DistanceMetric.EUCLIDEAN:
                        ops = "vector_l2_ops"        # L2 / Euclidean distance (<->)
                    else:
                        ops = "vector_ip_ops"        # Inner product / dot product (<#>)

                    # Create IVFFlat vector index for approximate nearest neighbor search
                    # lists=100 means 100 cluster centroids; tune based on data size
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx
                        ON {self.table_name}
                        USING ivfflat (embedding {ops})
                        WITH (lists = 100)
                    """)

                    # Create GIN index on JSONB metadata for fast @> containment queries
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_metadata_idx
                        ON {self.table_name}
                        USING gin (metadata)
                    """)

                    # Create B-Tree index on created_at for time-based ordering/filtering
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_created_at_idx
                        ON {self.table_name} (created_at DESC)
                    """)

                    # Commit all DDL statements together
                    conn.commit()

                    logger.info(f"Database schema initialized for {self.table_name}")

            # After schema is ready, enable RLS if requested
            if self.enable_rls:
                # Create the table, indexes, and optionally enable RLS
                with self._get_admin_connection() as admincon:
                    self._ensure_rls_enabled(admincon)

        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise VectorStoreException(f"Schema creation failed: {str(e)}")

    def _ensure_rls_enabled(self, conn=None) -> bool:
        """
        Enable Row Level Security on the table.
        Mirrors the ensure_rls_enabled() logic from get_vector_db.py.

        Uses module-level _rls_enabled_cache to avoid re-running ALTER TABLE
        on every instantiation (same as get_vector_db.py's _rls_enabled_cache).

        Args:
            conn: Optional existing connection; if None, borrows from pool.

        Returns:
            True if RLS is now enabled, False if it failed.
        """
        logger.info(f"::: ROW LEVEL SECURITY for {self.table_name} with role :{self.user_role}")
        # Check in-memory cache first — skip DB call if already done this session
        if self.table_name in _rls_enabled_cache:
            logger.info(f"RLS already enabled for {self.table_name} (cached)")
            return True

        try:
            # Use provided connection or get one from pool
            ctx = self._get_admin_connection() if conn is None else _NullContext(conn)

            with ctx as active_conn:
                with active_conn.cursor() as cur:

                    # Check pg_class to see if RLS is already enabled in the database
                    cur.execute("""
                        SELECT relrowsecurity, relforcerowsecurity
                        FROM pg_class
                        WHERE relname = %s
                    """, (self.table_name,))

                    rls_status = cur.fetchone()

                    # If both relrowsecurity AND relforcerowsecurity are True, RLS is already on
                    if rls_status and rls_status[0] and rls_status[1]:
                        # Add to cache so we skip this check next time
                        _rls_enabled_cache.add(self.table_name)
                        logger.info(f"RLS already enabled in database for {self.table_name} , role:{self.user_role}")
                        return True
                    
                    self.createPolicy(cur)

                    # Commit the security changes
                    active_conn.commit()

                    # Cache the result to avoid redundant ALTER TABLE calls
                    _rls_enabled_cache.add(self.table_name)
                    logger.info(f"RLS enabled successfully for {self.table_name} , role:{self.user_role}")
                    return True

        except Exception as e:
            # Log error but do NOT raise — RLS failure should not crash the app
            logger.error(f"Error enabling RLS for {self.table_name} , role:{self.user_role}: {str(e)}")
            return False


    def createPolicy(self,cur):
        logger.info(f"RLS CREATE POLICY BEGIN for {self.table_name} , role:{self.user_role}")
        if self.user_role:
             # DROP first to avoid duplicate policy error (works on all PG versions)
            cur.execute(f"DROP POLICY IF EXISTS insert_policy ON {self.table_name}")
            cur.execute(f"DROP POLICY IF EXISTS select_policy ON {self.table_name}")
            cur.execute(f"DROP POLICY IF EXISTS update_policy ON {self.table_name}")
            cur.execute(f"DROP POLICY IF EXISTS delete_policy ON {self.table_name}")

            # Recreate policies
            cur.execute(f"CREATE POLICY insert_policy ON {self.table_name} FOR INSERT TO {self.user_role} WITH CHECK (true)")
            cur.execute(f"CREATE POLICY select_policy ON {self.table_name} FOR SELECT TO {self.user_role} USING (true)")
            cur.execute(f"CREATE POLICY update_policy ON {self.table_name} FOR UPDATE TO {self.user_role} USING (true)")
            cur.execute(f"CREATE POLICY delete_policy ON {self.table_name} FOR DELETE TO {self.user_role} USING (true)")

            # Grant DML permissions
            cur.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {self.table_name} TO {self.user_role}")

            # Enable and force RLS
            cur.execute(f"ALTER TABLE {self.table_name} ENABLE ROW LEVEL SECURITY")
            cur.execute(f"ALTER TABLE {self.table_name} FORCE ROW LEVEL SECURITY")
            # Grant DML permissions to the specified user role
            cur.execute(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON {self.table_name} TO {self.user_role}"
            )
           

    def add_documents(self,
                      documents: List[Document],
                      embeddings: List[np.ndarray],
                      batch_size: int = 100) -> None:
        """
        Add documents with embeddings in batches for efficiency.
        Uses UPSERT (INSERT ... ON CONFLICT) so re-inserting same ID updates the record.

        Args:
            documents  : List of Document objects to store
            embeddings : Corresponding embedding vectors (must match documents length)
            batch_size : How many documents to insert per DB round-trip (default: 100)

        Raises:
            ValueError           : If documents and embeddings lengths don't match
            VectorStoreException : If DB insertion fails
        """
        # Validate that each document has a corresponding embedding
        if len(documents) != len(embeddings):
            raise ValueError(
                f"Documents ({len(documents)}) and embeddings ({len(embeddings)}) length mismatch"
            )

        # Nothing to do if lists are empty
        if not documents:
            logger.warning("No documents to add")
            return

        try:
            # Validate all embeddings have the correct dimension before inserting
            #embeddings = [np.array(emb) if not isinstance(emb, np.ndarray) else emb for emb in embeddings]
            embeddings = [
                np.array(emb).flatten()  # flatten handles 0-d, 2-d arrays → always 1D
                if not isinstance(emb, np.ndarray)
                else emb.flatten()
                for emb in embeddings
            ]
            for i, emb in enumerate(embeddings):
                self.validate_embedding(emb, self.dimension)
            logger.info(f"Embedding shape check: count={len(embeddings)}, dimension={len(embeddings[0])}")
            total_added = 0

            # Process documents in fixed-size batches to avoid memory/query size issues
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i + batch_size]   # Slice of documents
                batch_embs = embeddings[i:i + batch_size]  # Corresponding embeddings

                # Insert this batch into the database
                self._add_batch(batch_docs, batch_embs)
                total_added += len(batch_docs)
                logger.debug(f"Added batch {i // batch_size + 1}: {total_added}/{len(documents)}")

            logger.info(f"Successfully added {total_added} documents to {self.table_name}")

        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"Failed to add documents: {str(e)}")
            raise VectorStoreException(f"Document addition failed: {str(e)}")

    def _add_batch(self, documents: List[Document], embeddings: List[np.ndarray]) -> None:
        """
        Insert a single batch of documents using execute_values for performance.

        Args:
            documents  : Batch of Document objects
            embeddings : Corresponding embedding vectors
        """
        logger.info(f"::::: ADD BATCH ::: Begin :::::{self.table_name}")
        with self._get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    # Build list of tuples: (id, content, metadata_json, embedding_list)
                    batch_data = [
                        (
                            doc.id,
                            doc.content,
                            json.dumps(doc.metadata),   # Serialize metadata dict to JSON string
                            emb.tolist()                # Convert numpy array to plain Python list
                        )
                        for doc, emb in zip(documents, embeddings)
                    ]

                    # execute_values inserts all rows in one round-trip (much faster than executemany)
                    # ON CONFLICT updates existing rows with same id (upsert / idempotent)
                    extras.execute_values(
                        cur,
                        f"""
                        INSERT INTO {self.table_name} (id, content, metadata, embedding)
                        VALUES %s
                        ON CONFLICT (id) DO UPDATE SET
                            content    = EXCLUDED.content,
                            metadata   = EXCLUDED.metadata,
                            embedding  = EXCLUDED.embedding,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        batch_data,
                        template="(%s, %s, %s::jsonb, %s::vector)"  # Explicit casts for pgvector
                    )

                    # Commit this batch
                    conn.commit()
            except Exception as e:
                logger.error(f"single batch of documents failed: {str(e)}")
           

    def similarity_search(self,
                          query_embedding: np.ndarray,
                          k: int = 5,
                          filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Find the k most similar documents to the query embedding.
        Supports optional metadata filtering using JSONB containment (@>).

        Args:
            query_embedding : Query vector to search against
            k               : Number of top results to return (default: 5)
            filter          : Optional dict of metadata key-value filters
                              e.g. {"category": "tech"} returns only docs with that metadata

        Returns:
            List of Document objects ordered by similarity (highest first)

        Raises:
            VectorStoreException: If the search query fails
        """
        logger.info(f"similarity_search: table={self.table_name}, k={k}, filter={filter}")

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:

                    # Pick the correct pgvector distance operator for the chosen metric
                    if self.distance_metric == DistanceMetric.COSINE:
                        distance_op = "<=>"    # Cosine distance (0=identical, 2=opposite)
                    elif self.distance_metric == DistanceMetric.EUCLIDEAN:
                        distance_op = "<->"    # L2 / Euclidean distance
                    else:
                        distance_op = "<#>"    # Negative inner product (dot product)

                    # Base SELECT: compute distance from query embedding to each stored embedding
                    query = f"""
                        SELECT
                            id,
                            content,
                            metadata,
                            embedding {distance_op} %s::vector AS distance
                        FROM {self.table_name}
                    """

                    # First param is always the query embedding (converted to list)
                    params = [query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding]

                    # Append WHERE clause for each metadata filter key-value pair
                    if filter:
                        filter_conditions = []
                        for key, value in filter.items():
                            # @> is JSONB containment: metadata @> '{"key": "value"}'
                            filter_conditions.append("metadata @> %s::jsonb")
                            params.append(json.dumps({key: value}))

                        # Combine all filter conditions with AND
                        query += " WHERE " + " AND ".join(filter_conditions)

                    # ORDER BY distance ascending: smallest distance = most similar
                    query += " ORDER BY distance ASC LIMIT %s"
                    params.append(k)

                    # Execute the similarity search query
                    cur.execute(query, params)
                    results = cur.fetchall()

                    # Convert raw DB rows into Document objects
                    documents = []
                    for row in results:
                        doc = Document(
                            id=row['id'],
                            content=row['content'],
                            metadata=row['metadata'],
                            # Convert distance to similarity score: 1.0 = identical, 0.0 = no match
                            score=1.0 - float(row['distance'])
                        )
                        documents.append(doc)

                    logger.debug(f"Similarity search returned {len(documents)} results")
                    return documents

        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}")
            raise VectorStoreException(f"Search failed: {str(e)}")

    def delete_documents(self, ids: List[str]) -> int:
        """
        Delete documents by their IDs.

        Args:
            ids : List of document ID strings to delete

        Returns:
            Number of rows actually deleted

        Raises:
            VectorStoreException: If deletion fails
        """
        # Nothing to delete
        if not ids:
            return 0

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:

                    # ANY(%s) with a list param is more efficient than id IN (%s, %s, ...)
                    cur.execute(
                        f"DELETE FROM {self.table_name} WHERE id = ANY(%s)",
                        (ids,)
                    )

                    # rowcount gives number of rows affected by the last command
                    deleted_count = cur.rowcount
                    conn.commit()

                    logger.info(f"Deleted {deleted_count} documents from {self.table_name}")
                    return deleted_count

        except Exception as e:
            logger.error(f"Document deletion failed: {str(e)}")
            raise VectorStoreException(f"Deletion failed: {str(e)}")

    def get_document(self, doc_id: str) -> Optional[Document]:
        """
        Retrieve a single document by its ID.

        Args:
            doc_id : Document ID string

        Returns:
            Document object if found, None if not found
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:

                    # Fetch by primary key — fast point lookup
                    cur.execute(
                        f"SELECT id, content, metadata FROM {self.table_name} WHERE id = %s",
                        (doc_id,)
                    )
                    row = cur.fetchone()

                    # Return Document if row found, else None
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
        Get the total number of documents stored in this collection.

        Returns:
            Integer count of rows in the table (0 on error)
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # COUNT(*) is fast with a sequential scan; for huge tables consider pg_class estimate
                    cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                    count = cur.fetchone()[0]
                    return count

        except Exception as e:
            logger.error(f"Failed to count documents: {str(e)}")
            return 0

    def close(self) -> None:
        """Close all connections in the pool gracefully."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Closed all database connections")
        if self.connection_admin_pool:
            self.connection_admin_pool.closeall()


class _NullContext:
    """
    Trivial context manager wrapper around an already-open connection.
    Allows _ensure_rls_enabled() to accept an existing connection
    without opening a new one from the pool.
    """

    def __init__(self, conn):
        # Store the existing connection
        self._conn = conn

    def __enter__(self):
        # Return the connection as-is when entering the with block
        return self._conn

    def __exit__(self, *args):
        # Do NOT close or return the connection — caller owns it
        pass