# SparseRetriever.py
# BM25-based sparse retriever using ParadeDB (pg_search) extension on PostgreSQL

import logging
import psycopg2  # PostgreSQL adapter for Python
from typing import List
from rag.retriever.BaseRetriever import BaseRetriever       # your existing base class
from rag.retriever.Document import Document                  # your existing Document class
from rag.exception.RetrieverException import RetrieverException  # your existing exception

logger = logging.getLogger(__name__)


class SparseParaDBRetriever(BaseRetriever):
    """
    Sparse keyword-based retriever using BM25 via ParadeDB (pg_search).
    Connects directly to PostgreSQL and runs BM25 full-text search.
    """

    def __init__(self,
                 host: str,
                 port: int,
                 dbname: str,
                 user: str,
                 password: str,
                 table_name: str = "documents",       # table where documents are stored
                 content_column: str = "content",     # column containing document text
                 id_column: str = "id",               # column containing document ID
                 metadata_column: str = "metadata"):  # column containing metadata (JSON)
        """
        Initialize SparseRetriever with PostgreSQL + ParadeDB BM25.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            dbname: Database name
            user: DB username
            password: DB password
            table_name: Table where documents are stored
            content_column: Column with document text content
            id_column: Primary key column
            metadata_column: Column with JSON metadata
        """
        super().__init__(name="SparseRetriever")  # call BaseRetriever constructor

        # Store DB connection details
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = password
        self.table_name = table_name
        self.content_column = content_column
        self.id_column = id_column
        self.metadata_column = metadata_column

        # Establish DB connection on init
        self.connection = self._connect()

        # Ensure BM25 index exists on the content column via ParadeDB
        self._ensure_bm25_index()

        logger.info(f"SparseRetriever initialized on table '{table_name}' using ParadeDB BM25")

    def _connect(self):
        """
        Create and return a PostgreSQL connection.

        Returns:
            psycopg2 connection object

        Raises:
            RetrieverException: If connection fails
        """
        try:
            # Connect to PostgreSQL
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password
            )
            conn.autocommit = True  # auto-commit so DDL statements execute immediately
            logger.info("SparseRetriever: PostgreSQL connection established")
            return conn
        except Exception as e:
            logger.error(f"SparseRetriever: DB connection failed: {str(e)}")
            raise RetrieverException(f"DB connection failed: {str(e)}")

    def _ensure_bm25_index(self):
        """
        Creates a ParadeDB BM25 index on the content column if it doesn't exist.
        ParadeDB uses `CREATE INDEX ... USING bm25` syntax.
        """
        try:
            with self.connection.cursor() as cursor:
                # ParadeDB BM25 index creation using pg_search extension
                # This enables fast BM25 keyword search on the content column
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_bm25_index
                    ON {self.table_name}
                    USING bm25 ({self.id_column}, {self.content_column})
                    WITH (key_field = '{self.id_column}');
                """)
            logger.info(f"BM25 index ensured on table '{self.table_name}'")
        except Exception as e:
            # Log warning but don't crash — index may already exist or table may differ
            logger.warning(f"BM25 index creation skipped: {str(e)}")

    def retrieve(self, query: str, top_k: int = 10) -> List[Document]:
        """
        Retrieve documents using BM25 keyword search via ParadeDB.

        Args:
            query: The search query string
            top_k: Number of top documents to return

        Returns:
            List of Document objects ranked by BM25 score

        Raises:
            ValueError: If query is empty
            RetrieverException: If retrieval fails
        """
        # Validate query using base class method
        self.validate_query(query)

        try:
            with self.connection.cursor() as cursor:
                # ParadeDB BM25 search syntax:
                # Uses @@@ operator for BM25 full-text search
                # paradedb.bm25_query() constructs the search query
                # score_bm25() returns relevance score for ranking
                sql = f"""
                    SELECT
                        {self.id_column},                         -- document ID
                        {self.content_column},                    -- document text
                        {self.metadata_column},                   -- document metadata
                        paradedb.score({self.id_column}) AS bm25_score  -- BM25 relevance score
                    FROM {self.table_name}
                    WHERE {self.table_name} @@@ paradedb.parse(
                        '{self.content_column}',                  -- field to search
                        %s                                        -- query placeholder
                    )
                    ORDER BY bm25_score DESC                      -- highest score first
                    LIMIT %s;                                     -- limit results to top_k
                """

                # Execute query with safe parameterized inputs
                cursor.execute(sql, (query, top_k))

                # Fetch all matching rows
                rows = cursor.fetchall()

            # Convert rows to Document objects
            documents = []
            for row in rows:
                doc_id, content, metadata, score = row  # unpack each row

                # Build Document object (matches your existing Document class)
                doc = Document(
                    id=str(doc_id),          # document unique ID
                    content=content,          # raw text content
                    metadata=metadata or {},  # metadata dict (JSON from DB)
                    score=float(score)        # BM25 relevance score
                )
                documents.append(doc)

            logger.info(f"SparseRetriever: Retrieved {len(documents)} docs for query '{query[:50]}'")
            return documents

        except Exception as e:
            logger.error(f"SparseRetriever: BM25 retrieval failed: {str(e)}")
            raise RetrieverException(f"BM25 retrieval error: {str(e)}")

    def close(self):
        """
        Close the PostgreSQL connection gracefully.
        Call this when the retriever is no longer needed.
        """
        if self.connection and not self.connection.closed:
            self.connection.close()  # release DB connection
            logger.info("SparseRetriever: PostgreSQL connection closed")