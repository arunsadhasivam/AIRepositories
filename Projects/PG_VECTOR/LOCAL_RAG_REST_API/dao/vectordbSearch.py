"""
Vector Database with Multiple Retriever Types
- Dense Retriever: Vector similarity (default)
- BM25 Retriever: Keyword-based search
- Hybrid Retriever: Combines both approaches
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import execute_values
import numpy as np
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ABSTRACT INTERFACE
# ============================================================================

class VectorDBInterface(ABC):
    """
    Abstract interface for vector database with multiple retriever types
    """
    
    @abstractmethod
    def retrieve_dense(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Dense retriever - uses vector embeddings for semantic search
        
        Best for: Semantic similarity, conceptual matching
        """
        pass
    
    @abstractmethod
    def retrieve_bm25(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        BM25 retriever - uses keyword matching and term frequency
        
        Best for: Exact keyword matches, specific terms
        """
        pass
    
    @abstractmethod
    def retrieve_hybrid(self, query: str, top_k: int = 3, alpha: float = 0.5) -> List[Dict]:
        """
        Hybrid retriever - combines dense and BM25 retrievers
        
        Args:
            alpha: Weight for dense retriever (0.0 = only BM25, 1.0 = only dense)
        
        Best for: Balanced approach, most accurate results
        """
        pass
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 3, method: str = 'dense') -> List[Dict]:
        """
        Default retriever - select method dynamically
        
        Args:
            method: 'dense', 'bm25', or 'hybrid'
        """
        pass
    
    @abstractmethod
    def upsert_documents(self, documents: List[Dict]):
        """Add or update documents"""
        pass
    
    @abstractmethod
    def delete_document(self, document_id: str):
        """Delete single document"""
        pass
    
    @abstractmethod
    def delete_all(self):
        """Delete all documents"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if database is healthy"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict:
        """Get database statistics"""
        pass


# ============================================================================
# POSTGRESQL PGVECTOR IMPLEMENTATION WITH MULTIPLE RETRIEVERS
# ============================================================================

class PgVectorDB(VectorDBInterface):
    """
    PostgreSQL pgvector implementation with multiple retriever types
    
    Retriever Types:
    1. Dense Retriever: Vector similarity search (semantic)
    2. BM25 Retriever: Keyword-based search (lexical)
    3. Hybrid Retriever: Combines both approaches
    
    Installation:
        pip install psycopg2-binary sentence-transformers rank-bm25
    """
    
    def __init__(self, config: Dict):
        """
        Initialize PgVectorDB with multiple retrievers
        
        Args:
            config: Configuration with database credentials
        """
        # Database configuration
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 5432)
        self.database = config['database']
        self.user = config['user']
        self.password = config['password']
        self.table_name = config.get('table_name', 'documents')
        self.dimension = config.get('dimension', 384)
        self.model_name = config.get('model_name', 'all-MiniLM-L6-v2')
        
        # Initialize embedding model for dense retrieval
        logger.info(f"Loading embedding model: {self.model_name}")
        self.embedder = SentenceTransformer(self.model_name)
        
        # Initialize BM25 cache (will be populated on first use)
        self.bm25_index = None
        self.bm25_docs = None
        
        # Connect to database
        self._connect()
        self._create_table()
        
        logger.info(f"✅ PgVectorDB initialized with multiple retrievers")
    
    def _connect(self):
        """Establish PostgreSQL connection"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
            logger.info(f"✅ Connected to PostgreSQL: {self.database}")
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            raise
    
    def _create_table(self):
        """Create table with vector extension"""
        try:
            # Enable pgvector
            self.cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Create table
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id VARCHAR(255) PRIMARY KEY,
                text TEXT NOT NULL,
                embedding VECTOR({self.dimension}),
                source VARCHAR(500),
                page INTEGER,
                chunk_id VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            self.cursor.execute(create_table_sql)
            
            # Create vector index for dense retrieval
            create_index_sql = f"""
            CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx 
            ON {self.table_name} 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
            """
            self.cursor.execute(create_index_sql)
            
            # Create full-text search index for BM25
            create_fts_sql = f"""
            CREATE INDEX IF NOT EXISTS {self.table_name}_text_idx 
            ON {self.table_name} 
            USING gin(to_tsvector('english', text));
            """
            self.cursor.execute(create_fts_sql)
            
            logger.info(f"✅ Table created with vector and text indexes")
        except Exception as e:
            logger.error(f"Table creation error: {str(e)}")
            raise
    
    def retrieve_dense(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Dense retriever - semantic search using vector embeddings
        
        How it works:
        1. Convert query to embedding vector
        2. Find documents with similar vectors (cosine similarity)
        3. Return top_k most similar documents
        
        Advantages:
        - Understands semantic meaning
        - Works with synonyms and paraphrases
        - Good for conceptual questions
        
        Disadvantages:
        - May miss exact keyword matches
        - Slower than keyword search
        
        Args:
            query (str): Search query
            top_k (int): Number of documents to retrieve
            
        Returns:
            List[Dict]: Retrieved documents with scores
        
        Example:
            # Query: "employee vacation days"
            # Will match: "staff annual leave" (semantic similarity)
            docs = vector_db.retrieve_dense("employee vacation days", top_k=3)
        """
        try:
            logger.info(f"[DENSE] Retrieving for: '{query[:50]}...'")
            
            # Step 1: Generate query embedding
            query_embedding = self.embedder.encode(query)
            embedding_str = '[' + ','.join(map(str, query_embedding.tolist())) + ']'
            
            # Step 2: Vector similarity search
            retrieve_sql = f"""
            SELECT 
                id,
                text,
                source,
                page,
                chunk_id,
                1 - (embedding <=> %s::vector) AS score
            FROM {self.table_name}
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """
            
            self.cursor.execute(retrieve_sql, (embedding_str, embedding_str, top_k))
            
            # Step 3: Format results
            rows = self.cursor.fetchall()
            docs = []
            for row in rows:
                docs.append({
                    "id": row[0],
                    "content": row[1],
                    "score": float(row[5]),
                    "retriever": "dense",
                    "metadata": {
                        "source": row[2] or "",
                        "page": row[3] or 0,
                        "chunk_id": row[4] or ""
                    }
                })
            
            logger.info(f"[DENSE] Retrieved {len(docs)} documents")
            return docs
            
        except Exception as e:
            logger.error(f"Dense retrieval error: {str(e)}")
            return []
    
    def retrieve_bm25(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        BM25 retriever - keyword-based search using term frequency
        
        How it works:
        1. Tokenize query into keywords
        2. Score documents based on keyword frequency and rarity
        3. Return top_k highest scoring documents
        
        Advantages:
        - Fast keyword matching
        - Good for specific terms/names
        - No embedding computation needed
        
        Disadvantages:
        - No semantic understanding
        - Requires exact keyword matches
        - Misses synonyms
        
        Args:
            query (str): Search query
            top_k (int): Number of documents to retrieve
            
        Returns:
            List[Dict]: Retrieved documents with BM25 scores
        
        Example:
            # Query: "OAuth 2.0"
            # Will match: documents containing exact term "OAuth 2.0"
            docs = vector_db.retrieve_bm25("OAuth 2.0", top_k=3)
        """
        try:
            logger.info(f"[BM25] Retrieving for: '{query[:50]}...'")
            
            # Step 1: Load all documents for BM25 (cache if needed)
            if self.bm25_index is None:
                self._build_bm25_index()
            
            # Step 2: Tokenize query
            query_tokens = self._tokenize(query)
            
            # Step 3: Get BM25 scores for all documents
            scores = self.bm25_index.get_scores(query_tokens)
            
            # Step 4: Get top_k document indices
            top_indices = np.argsort(scores)[::-1][:top_k]
            
            # Step 5: Format results
            docs = []
            for idx in top_indices:
                if scores[idx] > 0:  # Only include documents with non-zero score
                    doc_data = self.bm25_docs[idx]
                    docs.append({
                        "id": doc_data['id'],
                        "content": doc_data['text'],
                        "score": float(scores[idx]),
                        "retriever": "bm25",
                        "metadata": doc_data['metadata']
                    })
            
            logger.info(f"[BM25] Retrieved {len(docs)} documents")
            return docs
            
        except Exception as e:
            logger.error(f"BM25 retrieval error: {str(e)}")
            return []
    
    def retrieve_hybrid(self, query: str, top_k: int = 3, alpha: float = 0.5) -> List[Dict]:
        """
        Hybrid retriever - combines dense and BM25 retrievers
        
        How it works:
        1. Get results from both dense and BM25 retrievers
        2. Normalize scores from both methods
        3. Combine scores: final_score = alpha * dense + (1-alpha) * bm25
        4. Re-rank and return top_k documents
        
        Advantages:
        - Best of both worlds
        - Semantic understanding + keyword matching
        - Most accurate results
        
        Disadvantages:
        - Slower (runs both retrievers)
        - More complex
        
        Args:
            query (str): Search query
            top_k (int): Number of documents to retrieve
            alpha (float): Weight for dense retriever
                - 0.0 = only BM25 (keyword-based)
                - 0.5 = equal weight (default)
                - 1.0 = only dense (semantic)
            
        Returns:
            List[Dict]: Retrieved documents with combined scores
        
        Example:
            # Balanced approach (alpha=0.5)
            docs = vector_db.retrieve_hybrid("employee leave policy", top_k=3, alpha=0.5)
            
            # Prefer semantic (alpha=0.7)
            docs = vector_db.retrieve_hybrid("vacation days", top_k=3, alpha=0.7)
            
            # Prefer keywords (alpha=0.3)
            docs = vector_db.retrieve_hybrid("OAuth 2.0 token", top_k=3, alpha=0.3)
        """
        try:
            logger.info(f"[HYBRID] Retrieving for: '{query[:50]}...' (alpha={alpha})")
            
            # Step 1: Get results from both retrievers
            # Retrieve more than top_k to have enough for re-ranking
            dense_docs = self.retrieve_dense(query, top_k=top_k * 2)
            bm25_docs = self.retrieve_bm25(query, top_k=top_k * 2)
            
            # Step 2: Normalize scores to [0, 1] range
            def normalize_scores(docs):
                if not docs:
                    return docs
                scores = [d['score'] for d in docs]
                min_score = min(scores)
                max_score = max(scores)
                if max_score == min_score:
                    for d in docs:
                        d['normalized_score'] = 1.0
                else:
                    for d in docs:
                        d['normalized_score'] = (d['score'] - min_score) / (max_score - min_score)
                return docs
            
            dense_docs = normalize_scores(dense_docs)
            bm25_docs = normalize_scores(bm25_docs)
            
            # Step 3: Combine scores
            combined_scores = {}
            
            # Add dense scores
            for doc in dense_docs:
                doc_id = doc['id']
                combined_scores[doc_id] = {
                    'doc': doc,
                    'dense_score': doc.get('normalized_score', 0),
                    'bm25_score': 0
                }
            
            # Add BM25 scores
            for doc in bm25_docs:
                doc_id = doc['id']
                if doc_id in combined_scores:
                    combined_scores[doc_id]['bm25_score'] = doc.get('normalized_score', 0)
                else:
                    combined_scores[doc_id] = {
                        'doc': doc,
                        'dense_score': 0,
                        'bm25_score': doc.get('normalized_score', 0)
                    }
            
            # Step 4: Calculate hybrid scores
            hybrid_docs = []
            for doc_id, scores in combined_scores.items():
                # Hybrid score = alpha * dense + (1-alpha) * bm25
                hybrid_score = alpha * scores['dense_score'] + (1 - alpha) * scores['bm25_score']
                
                doc = scores['doc'].copy()
                doc['score'] = hybrid_score
                doc['retriever'] = 'hybrid'
                doc['dense_score'] = scores['dense_score']
                doc['bm25_score'] = scores['bm25_score']
                
                hybrid_docs.append(doc)
            
            # Step 5: Sort by hybrid score and return top_k
            hybrid_docs.sort(key=lambda x: x['score'], reverse=True)
            result_docs = hybrid_docs[:top_k]
            
            logger.info(f"[HYBRID] Retrieved {len(result_docs)} documents")
            return result_docs
            
        except Exception as e:
            logger.error(f"Hybrid retrieval error: {str(e)}")
            return []
    
    def retrieve(self, query: str, top_k: int = 3, method: str = 'dense') -> List[Dict]:
        """
        Default retriever - select method dynamically
        
        Args:
            query (str): Search query
            top_k (int): Number of documents to retrieve
            method (str): Retriever type - 'dense', 'bm25', or 'hybrid'
            
        Returns:
            List[Dict]: Retrieved documents
        
        Example:
            # Use dense retriever (default)
            docs = vector_db.retrieve("query", method='dense')
            
            # Use BM25 retriever
            docs = vector_db.retrieve("query", method='bm25')
            
            # Use hybrid retriever
            docs = vector_db.retrieve("query", method='hybrid')
        """
        if method == 'dense':
            return self.retrieve_dense(query, top_k)
        elif method == 'bm25':
            return self.retrieve_bm25(query, top_k)
        elif method == 'hybrid':
            return self.retrieve_hybrid(query, top_k)
        else:
            logger.warning(f"Unknown method '{method}', using dense")
            return self.retrieve_dense(query, top_k)
    
    def _build_bm25_index(self):
        """
        Build BM25 index from all documents in database
        
        Called automatically on first BM25 retrieval
        """
        try:
            logger.info("Building BM25 index...")
            
            # Fetch all documents
            fetch_sql = f"SELECT id, text, source, page, chunk_id FROM {self.table_name};"
            self.cursor.execute(fetch_sql)
            rows = self.cursor.fetchall()
            
            # Store documents
            self.bm25_docs = []
            tokenized_corpus = []
            
            for row in rows:
                doc = {
                    'id': row[0],
                    'text': row[1],
                    'metadata': {
                        'source': row[2] or "",
                        'page': row[3] or 0,
                        'chunk_id': row[4] or ""
                    }
                }
                self.bm25_docs.append(doc)
                
                # Tokenize document text
                tokens = self._tokenize(row[1])
                tokenized_corpus.append(tokens)
            
            # Create BM25 index
            self.bm25_index = BM25Okapi(tokenized_corpus)
            
            logger.info(f"✅ BM25 index built with {len(self.bm25_docs)} documents")
            
        except Exception as e:
            logger.error(f"BM25 index building error: {str(e)}")
            raise
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens (lowercase, alphanumeric only)
        """
        # Convert to lowercase
        text = text.lower()
        
        # Split on non-alphanumeric characters
        tokens = re.findall(r'\w+', text)
        
        return tokens
    
    def upsert_documents(self, documents: List[Dict]):
        """
        Add or update documents
        
        Also rebuilds BM25 index to include new documents
        """
        try:
            logger.info(f"Upserting {len(documents)} documents...")
            
            # Generate embeddings
            texts = [doc['text'] for doc in documents]
            embeddings = self.embedder.encode(texts, show_progress_bar=False)
            
            # Prepare data
            values = []
            for doc, embedding in zip(documents, embeddings):
                embedding_str = '[' + ','.join(map(str, embedding.tolist())) + ']'
                values.append((
                    doc['id'],
                    doc['text'],
                    embedding_str,
                    doc.get('source', ''),
                    doc.get('page', 0),
                    doc.get('chunk_id', '')
                ))
            
            # Insert
            upsert_sql = f"""
            INSERT INTO {self.table_name} (id, text, embedding, source, page, chunk_id)
            VALUES %s
            ON CONFLICT (id) 
            DO UPDATE SET
                text = EXCLUDED.text,
                embedding = EXCLUDED.embedding,
                source = EXCLUDED.source,
                page = EXCLUDED.page,
                chunk_id = EXCLUDED.chunk_id,
                created_at = CURRENT_TIMESTAMP;
            """
            
            execute_values(self.cursor, upsert_sql, values)
            
            # Rebuild BM25 index
            self.bm25_index = None  # Invalidate cache
            
            logger.info(f"✅ Upserted {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Upsert error: {str(e)}")
            raise
    
    def delete_document(self, document_id: str):
        """Delete document and rebuild BM25 index"""
        try:
            delete_sql = f"DELETE FROM {self.table_name} WHERE id = %s;"
            self.cursor.execute(delete_sql, (document_id,))
            
            # Invalidate BM25 cache
            self.bm25_index = None
            
            logger.info(f"✅ Deleted document: {document_id}")
        except Exception as e:
            logger.error(f"Delete error: {str(e)}")
            raise
    
    def delete_all(self):
        """Delete all documents"""
        try:
            delete_sql = f"DELETE FROM {self.table_name};"
            self.cursor.execute(delete_sql)
            
            # Clear BM25 cache
            self.bm25_index = None
            self.bm25_docs = None
            
            logger.info("✅ Deleted all documents")
        except Exception as e:
            logger.error(f"Delete all error: {str(e)}")
            raise
    
    def health_check(self) -> bool:
        """Check database health"""
        try:
            self.cursor.execute("SELECT 1;")
            return self.cursor.fetchone()[0] == 1
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        try:
            count_sql = f"SELECT COUNT(*) FROM {self.table_name};"
            self.cursor.execute(count_sql)
            total_docs = self.cursor.fetchone()[0]
            
            size_sql = f"SELECT pg_size_pretty(pg_total_relation_size('{self.table_name}'));"
            self.cursor.execute(size_sql)
            table_size = self.cursor.fetchone()[0]
            
            return {
                "total_documents": total_docs,
                "dimension": self.dimension,
                "table_name": self.table_name,
                "table_size": table_size,
                "bm25_indexed": self.bm25_index is not None
            }
        except Exception as e:
            return {"error": str(e)}
    
    def close(self):
        """Close database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            logger.info("✅ Connection closed")
        except Exception as e:
            logger.error(f"Close error: {str(e)}")


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_retriever_types():
    """
    Example: Different retriever types
    """
    print("\n" + "="*80)
    print("EXAMPLE: Different Retriever Types")
    print("="*80)
    
    config = {
        'host': 'localhost',
        'database': 'vectordb',
        'user': 'postgres',
        'password': 'your_password'
    }
    
    vector_db: VectorDBInterface = PgVectorDB(config)
    
    # Add sample documents
    documents = [
        {
            'id': 'doc_001',
            'text': 'Employees receive 20 days of annual leave per year.',
            'source': 'handbook.pdf'
        },
        {
            'id': 'doc_002',
            'text': 'Our API uses OAuth 2.0 authentication with bearer tokens.',
            'source': 'api_docs.pdf'
        }
    ]
    vector_db.upsert_documents(documents)
    
    query = "vacation days for employees"
    
    # Method 1: Dense retriever (semantic)
    print("\n1. Dense Retriever (Semantic):")
    dense_docs = vector_db.retrieve_dense(query, top_k=2)
    for doc in dense_docs:
        print(f"   Score: {doc['score']:.3f} - {doc['content'][:60]}...")
    
    # Method 2: BM25 retriever (keyword)
    print("\n2. BM25 Retriever (Keyword):")
    bm25_docs = vector_db.retrieve_bm25(query, top_k=2)
    for doc in bm25_docs:
        print(f"   Score: {doc['score']:.3f} - {doc['content'][:60]}...")
    
    # Method 3: Hybrid retriever (combined)
    print("\n3. Hybrid Retriever (Combined):")
    hybrid_docs = vector_db.retrieve_hybrid(query, top_k=2, alpha=0.5)
    for doc in hybrid_docs:
        print(f"   Score: {doc['score']:.3f} - {doc['content'][:60]}...")
        print(f"   (Dense: {doc['dense_score']:.3f}, BM25: {doc['bm25_score']:.3f})")
    
    vector_db.close()


def example_when_to_use_which():
    """
    Example: When to use which retriever
    """
    print("\n" + "="*80)
    print("EXAMPLE: When to Use Which Retriever")
    print("="*80)
    
    print("""
    Query Type              | Best Retriever | Why
    ------------------------|----------------|---------------------------
    "OAuth 2.0 token"       | BM25           | Exact technical term
    "employee vacation"     | Dense          | Synonym for "leave"
    "annual leave policy"   | Hybrid         | Both keywords + meaning
    "API authentication"    | Dense          | Conceptual query
    "section 4.2.1"         | BM25           | Exact reference
    
    General Guidelines:
    - Dense: Conceptual, paraphrased queries
    - BM25: Exact terms, technical names, references
    - Hybrid: Best overall accuracy (recommended)
    """)


if __name__ == "__main__":
    print("=" * 80)
    print("VECTOR DATABASE WITH MULTIPLE RETRIEVER TYPES")
    print("=" * 80)
    
    print("""
    Available Retrievers:
    
    1. retrieve_dense(query, top_k)
       → Semantic search using vector embeddings
       → Best for: Conceptual queries, synonyms
    
    2. retrieve_bm25(query, top_k)
       → Keyword-based search using BM25
       → Best for: Exact terms, technical names
    
    3. retrieve_hybrid(query, top_k, alpha)
       → Combines dense + BM25
       → Best for: Most accurate results
    
    4. retrieve(query, top_k, method='dense|bm25|hybrid')
       → Dynamic method selection
    
    Installation:
        pip install psycopg2-binary sentence-transformers rank-bm25
    """)
    
    # Uncomment to run examples
    # example_retriever_types()
    # example_when_to_use_which()


