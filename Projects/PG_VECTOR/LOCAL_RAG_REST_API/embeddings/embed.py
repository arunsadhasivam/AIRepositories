import os
from datetime import datetime
from werkzeug.utils import secure_filename

from langchain_community.document_loaders.pdf import UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from embeddings.get_vector_db import get_vector_db
#pii masking
from langchain_core.documents import Document
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

from sqlalchemy.exc import ProgrammingError, OperationalError
import psycopg2
import logging


TEMP_FOLDER = os.getenv('TEMP_FOLDER', './_temp')

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
def embed(file,user_role,pwd):
    logging.info(f'::::: EMBEDDING TO VECTOR DB:BEGIN:::{user_role}')
    # Check if the file is valid, save it, load and split the data, add to the database, and remove the temporary file
    if file.filename != '' and file and allowed_file(file.filename):
        file_path = save_file(file)
        chunks = load_and_split_data(file_path)
        #pii mask
        #chunks= createmask(chunks)
        db = get_vector_db(user_role,pwd)
        try:
            logging.info(f'::::: INSERT TO VECTOR DB:BEGIN {user_role}:::')
            db.add_documents(chunks)
            logging.info('::::: INSERT TO VECTOR DB:END:::')
        except ProgrammingError as e:
            logging.info('::::: INSERT TO VECTOR DB:BEGIN:::PERMISSION ERROR')
            if "row-level security" in str(e).lower() or "permission denied" in str(e).lower():
                return False
            else:
                raise
        except psycopg2.errors.InsufficientPrivilege:
            return False
        #pgVector auto save 
        #db.persist()
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

