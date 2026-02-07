import os
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores.pgvector import PGVector
# Environment variable configuration
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'default-local-rag')
TEXT_EMBEDDING_MODEL = os.getenv('TEXT_EMBEDDING_MODEL', 'default-nomic-embed-text')
from sqlalchemy.exc import ProgrammingError, OperationalError

import logging

# PostgreSQL connection string format:
# postgresql+psycopg2://user:password@host:port/dbname
PG_CONNECTION_STRING = os.getenv(
    'PG_CONNECTION_STRING',
    'postgresql+psycopg2://arun:arun@localhost:5432/rag' #default
)

def get_vector_db(user_role,pwd):
    db= None
    try:
        # Initialize the embedding model (same as before)
        embedding = OllamaEmbeddings(model=TEXT_EMBEDDING_MODEL, show_progress=True)
        PG_CONNECTION_STRING=  f'postgresql+psycopg2://{user_role}:{pwd}@localhost:5432/rag' 
        logging.info(f'::::: DBCONNECTION: GETTING CONNECTION ::::={PG_CONNECTION_STRING}')
        # PGVector automatically creates the table and pgvector extension if not exists
        db = PGVector(
            collection_name=COLLECTION_NAME,
            connection_string=PG_CONNECTION_STRING,
            embedding_function=embedding,
            use_jsonb=True
        )
    except ProgrammingError as e:
        logging.info(f'::::: DBCONNECTION: GETTING CONNECTION :: ERROR={PG_CONNECTION_STRING}')

    return db