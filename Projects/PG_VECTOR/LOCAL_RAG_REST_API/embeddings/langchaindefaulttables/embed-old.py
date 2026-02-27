import os
from datetime import datetime
from werkzeug.utils import secure_filename

from langchain_community.document_loaders.pdf import UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
#pii masking
from langchain_core.documents import Document
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()
from rag.vectorstore.PgVectorStore import PgVectorStore
from sqlalchemy.exc import ProgrammingError, OperationalError
import psycopg2
import logging
from prompt.query import getPgVectorStore
from rag.retriever.Document import Document as RagDocument
from langchain_community.embeddings import OllamaEmbeddings
import uuid
TEMP_FOLDER = os.getenv('TEMP_FOLDER', './_temp')
TEXT_EMBEDDING_MODEL = os.getenv('TEXT_EMBEDDING_MODEL', 'nomic-embed-text')

# Function to check if the uploaded file is allowed (only PDF files)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}

# Function to save the uploaded file to the temporary folder
def save_file(file):
    # Save the uploaded file with a secure filename and return the file path
    ct = datetime.now()
    ts = ct.timestamp()
    filename = str(ts) + "_" + secure_filename(file.filename)
    file_path = os.path.join(TEMP_FOLDER, filename)
    file.save(file_path)

    return file_path

# Function to load and split the data from the PDF file
def load_and_split_data(file_path):
    # Load the PDF file and split the data into chunks
    loader = UnstructuredPDFLoader(file_path=file_path)
    data = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=7500, chunk_overlap=100)
    chunks = text_splitter.split_documents(data)

    return chunks


# Main function to handle the embedding process
def embed(file, user_role, pwd):
    logging.info(f'::::: EMBEDDING TO VECTOR DB:BEGIN:::{user_role}')
    if file.filename != '' and file and allowed_file(file.filename):
        file_path = save_file(file)
        chunks = load_and_split_data(file_path)
        
        # Get PgVectorStore instance
        db = getPgVectorStore(user_role, pwd)
        
        try:
            logging.info(f'::::: INSERT TO VECTOR DB:BEGIN {user_role}:::')
            
            # Step 1 - Convert LangChain chunks to RagDocument
            rag_docs = [
                RagDocument(
                    id=str(uuid.uuid4()),
                    content=chunk.page_content,
                    metadata=chunk.metadata
                )
                for chunk in chunks
            ]
            
            # Step 2 - Generate embeddings using same model as search
            embedding_model = OllamaEmbeddings(model=TEXT_EMBEDDING_MODEL, show_progress=True)
            vectors = embedding_model.embed_documents([doc.content for doc in rag_docs])
            numpy_vectors = [np.array(v) for v in vectors]  # convert list → numpy array
            # Step 3 - Insert into PgVectorStore
            db.add_documents(rag_docs, numpy_vectors)
            
            logging.info('::::: INSERT TO VECTOR DB:END:::')
            
        except ProgrammingError as e:
            logging.info('::::: INSERT TO VECTOR DB:BEGIN:::PERMISSION ERROR')
            if "row-level security" in str(e).lower() or "permission denied" in str(e).lower():
                return False
            else:
                raise
        except psycopg2.errors.InsufficientPrivilege:
            return False
        
        os.remove(file_path)
        return True
    return False

def createmask(chunks):
       # Mask PII in each chunk before inserting
    masked_chunks = []
    for chunk in chunks:
        masked_content = mask_pii(chunk.page_content)
        masked_chunks.append(
            Document(
                page_content=masked_content,
                metadata=chunk.metadata
            )
        )
    return masked_chunks

def mask_pii(text: str) -> str:
    # Analyze the text to detect all PII entities
    results = analyzer.analyze(
        text=text,
        language="en"
    )
    
    # If no PII detected, return original text as is
    if not results:
        return text
    
    # Replace detected PII with placeholder labels
    masked_text = anonymizer.anonymize(
        text=text,
        analyzer_results=results
    ).text
    

    return masked_text

