import os
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores.pgvector import PGVector
from rag.vectorstore.PgVectorStore import PgVectorStore
from sqlalchemy.exc import ProgrammingError, OperationalError
from sqlalchemy import text, create_engine
from sqlalchemy.pool import QueuePool
import logging
import time

# Environment variable configuration
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'default-local-rag')
TEXT_EMBEDDING_MODEL = os.getenv('TEXT_EMBEDDING_MODEL', 'default-nomic-embed-text')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'rag')

# PostgreSQL connection string format:
# postgresql+psycopg2://user:password@host:port/dbname
PG_CONNECTION_STRING = os.getenv(
    'PG_CONNECTION_STRING',
    'postgresql+psycopg2://arun:arun@localhost:5432/rag'  # default
)

# Cache for database connections per user
_db_cache = {}
# Track which tables have RLS enabled to avoid repeated ALTER TABLE
_rls_enabled_cache = set()


def ensure_rls_enabled(engine, COLLECTION_NAME):
    """
    Ensure RLS is enabled on the collection table.
    Only runs once per collection per application lifetime.
    
    Args:
        engine: SQLAlchemy engine
        COLLECTION_NAME (str): Name of the collection
        
    Returns:
        bool: True if RLS is enabled, False otherwise
    """
    # Check if already enabled in this session
    if COLLECTION_NAME in _rls_enabled_cache:
        # Log that RLS is already cached
        logging.info(f':::::: RLS already enabled for {COLLECTION_NAME} (cached):::::')
        # Return True since RLS is enabled
        return True
    
    try:
        # Execute RLS commands using engine connection
        with engine.connect() as conn:
            # Check if RLS is already enabled in database
            result = conn.execute(text("""
                SELECT relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relname = 'langchain_pg_embedding'
            """))
            # Fetch RLS status from query result
            rls_status = result.fetchone()
            
            # If already enabled in database, add to cache and return
            if rls_status and rls_status[0] and rls_status[1]:
                # Add collection to RLS enabled cache
                _rls_enabled_cache.add(COLLECTION_NAME)
                # Log that RLS is already enabled
                logging.info(f':::::: RLS already enabled in database for {COLLECTION_NAME} :::::: ')
                # Return True
                return True
            
            # Enable RLS on the table
            conn.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON langchain_pg_embedding TO app_admin"))
            conn.execute(text("ALTER TABLE langchain_pg_embedding ENABLE ROW LEVEL SECURITY"))
            # Force RLS on the table
            conn.execute(text("ALTER TABLE langchain_pg_embedding FORCE ROW LEVEL SECURITY"))
            # Commit the changes
            conn.commit()
            
            # Add collection to cache
            _rls_enabled_cache.add(COLLECTION_NAME)
            # Log successful RLS enablement
            logging.info(f'::::::  RLS enabled successfully for {COLLECTION_NAME} :::::: ')
            # Return True for success
            return True
            
    except Exception as e:
        # Log error but don't fail the connection
        logging.error(f'Error ensuring RLS enabled: {str(e)}')
        # Return False to indicate failure
        return False

def get_pg_vector_connection(user_role,pwd):
    PG_CONNECTION_STRING = f'postgresql+psycopg2://{user_role}:{pwd}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    return PG_CONNECTION_STRING

def get_vector_db(user_role, pwd, max_retries=3, retry_delay=1):
    """
    Get or create vector database connection with connection pooling and retry logic.
    
    Args:
        user_role (str): Database user role
        pwd (str): Database password
        max_retries (int): Maximum number of connection retry attempts
        retry_delay (int): Delay in seconds between retries
        
    Returns:
        PGVector: Vector database instance
        
    Raises:
        Exception: If connection fails after all retries
    """
    # Initialize db variable
    db = None
    
    # Create cache key based on user credentials
    cache_key = f"{user_role}:{DB_HOST}:{DB_PORT}:{DB_NAME}:{COLLECTION_NAME}"
    logging.info(f':::::: DB CONNECTION :::get_vector_db {user_role} :::::: ')
    
    #Return cached connection if exists and is valid
    if cache_key in _db_cache:
        # Get database from cache
        db = _db_cache[cache_key]
        # Validate connection is still alive
        try:
            # Simple validation query
            db.similarity_search("test", k=1)
            # Log using cached connection
            logging.info(f':::::: DB CONNECTION :::Using cached connection for {user_role} :::::: ')
            # Return cached database connection
            return db
        except Exception as e:
            # Connection is stale, log warning
            logging.warning(f'::::::   Cached connection invalid, recreating: {str(e)}')
            # Remove stale connection from cache
            del _db_cache[cache_key]
    
    # # Initialize variable to track last error
    last_error = None
    
    # Attempt to create new connection with retries
    for attempt in range(max_retries):
        try:
            # Build connection string from user credentials and environment variables
            PG_CONNECTION_STRING = f'postgresql+psycopg2://{user_role}:{pwd}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
            pg_vector_dsn = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={user_role} password={pwd}"

            # Log connection attempt
            logging.info(f'::::: DBCONNECTION: GETTING CONNECTION Attempt {attempt + 1}/{max_retries} ::::={PG_CONNECTION_STRING}')
            
            # # Create SQLAlchemy engine with connection pooling
            # engine = create_engine(
            #     PG_CONNECTION_STRING,
            #     poolclass=QueuePool,  # Use queue-based connection pooling
            #     pool_size=5,  # Number of connections to maintain in pool
            #     max_overflow=10,  # Additional connections if pool is full
            #     pool_timeout=30,  # Timeout in seconds waiting for connection from pool
            #     pool_pre_ping=True,  # Verify connections before using them
            #     pool_recycle=3600  # Recycle connections after 1 hour
            # )
            
            # Initialize the embedding model (same as before)
            embedding = OllamaEmbeddings(model=TEXT_EMBEDDING_MODEL, show_progress=True)
            
            # PGVector automatically creates the table and pgvector extension if not exists
            db = PgVectorStore(
                collection_name=COLLECTION_NAME,
                connection_string=pg_vector_dsn,
                embedding_function=embedding,
                use_jsonb=True
            )
            
            # Ensure RLS is enabled (runs only once per collection)
           # ensure_rls_enabled(engine, COLLECTION_NAME)
            
            # Test connection with simple query to validate it works
            try:
                # Verify connection works with similarity search
                db.similarity_search("connection_test", k=1)
                # Log connection validation success
                logging.info(f'::::: DBCONNECTION: Connection validated for {user_role}')
            except Exception as test_error:
                # Log validation warning but continue
                logging.warning(f'Connection validation failed: {str(test_error)}')
            
            # Cache the connection for reuse
            _db_cache[cache_key] = db
            
            # Log success
            logging.info(f'::::: DBCONNECTION: Successfully connected for {user_role}')
            
            # Return database connection
            return db
            
        except ProgrammingError as e:
            # Log programming error with attempt number
            logging.error(f'::::: DBCONNECTION: GETTING CONNECTION :: PROGRAMMING ERROR Attempt {attempt + 1}={str(e)}')
            # Store last error for final exception
            last_error = e
            
        except OperationalError as e:
            # Log operational error with attempt number
            logging.error(f'::::: DBCONNECTION: GETTING CONNECTION :: OPERATIONAL ERROR Attempt {attempt + 1}={str(e)}')
            # Store last error for final exception
            last_error = e
            
        except Exception as e:
            # Log unexpected error with attempt number
            logging.error(f'::::: DBCONNECTION: GETTING CONNECTION :: UNEXPECTED ERROR Attempt {attempt + 1}={str(e)}')
            # Store last error for final exception
            last_error = e
        
        # Wait before retry (except on last attempt)
        if attempt < max_retries - 1:
            # Log retry information
            logging.info(f'Retrying in {retry_delay} seconds...')
            # Sleep before next retry
            time.sleep(retry_delay)
    
    # All retries failed - raise exception
    error_msg = f'Failed to connect to database after {max_retries} attempts'
    # Log final error
    logging.error(f'::::: DBCONNECTION: {error_msg}')
    # Raise exception with error details
    raise Exception(f'{error_msg}. Last error: {str(last_error)}')


def clear_connection_cache():
    """
    Clear the database connection cache.
    Call this when you want to force reconnection.
    """
    # Access global cache variables
    global _db_cache, _rls_enabled_cache
    # Clear connection cache dictionary
    _db_cache.clear()
    # Clear RLS enabled cache set
    _rls_enabled_cache.clear()
    # Log cache cleared
    logging.info('Database connection cache cleared')