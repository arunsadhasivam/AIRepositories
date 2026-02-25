"""
embed.py - Document Embedding Module

This module provides functionality to embed multiple document formats (PDF, Word, Markdown, HTML)
into a vector database with support for PII masking using Docling for document processing.
"""

import os
from datetime import datetime
from werkzeug.utils import secure_filename
from langchain_text_splitters import RecursiveCharacterTextSplitter
from embeddings.get_vector_db import get_vector_db
from langchain_core.documents import Document
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from sqlalchemy.exc import ProgrammingError, OperationalError
import psycopg2
import logging
from indexer.SolrIndexer import SolrIndexer

import uuid  # for generating unique document IDs


class DocumentEmbedder:
    """
    Handles multiple document format embedding into vector database with PII masking support.
    Supports: PDF, Word (DOCX/DOC), Markdown (MD), HTML
    """
    
    def __init__(self, temp_folder=None, max_file_size=None, chunk_size=7500, chunk_overlap=100):
        """
        Initialize DocumentEmbedder with configuration parameters.
        
        Args:
            temp_folder (str): Temporary folder path for file storage
            max_file_size (int): Maximum allowed file size in bytes
            chunk_size (int): Size of text chunks for splitting
            chunk_overlap (int): Overlap between chunks
        """
        # Set temporary folder from parameter or environment variable or default
        self.temp_folder = temp_folder or os.getenv('TEMP_FOLDER', './_temp')
        # Set max file size (default 50MB if not provided)
        self.max_file_size = max_file_size or int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024))
        # Define allowed file extensions - PDF, Word, Markdown, HTML
        self.allowed_extensions = {'pdf', 'docx', 'doc', 'md', 'html', 'htm'}
        # Set chunk size for text splitting
        self.chunk_size = chunk_size
        # Set overlap between chunks
        self.chunk_overlap = chunk_overlap
        
        # Initialize PII analyzer engine for detecting sensitive information
        self.analyzer = AnalyzerEngine()
        # Initialize PII anonymizer engine for masking sensitive information
        self.anonymizer = AnonymizerEngine()
        self.solrIndexer = SolrIndexer()
        from docling.document_converter import DocumentConverter
        # Initialize Docling document converter for multi-format processing
        self.converter = DocumentConverter()
        
        # Create temporary folder if it doesn't exist
        os.makedirs(self.temp_folder, exist_ok=True)
        
        # Log successful initialization
        logging.info('DocumentEmbedder initialized successfully')
    
    def allowed_file(self, filename):
        """
        Check if the uploaded file extension is allowed.
        Supports: PDF, DOCX, DOC, MD, HTML, HTM
        
        Args:
            filename (str): Name of the file to check
            
        Returns:
            bool: True if file extension is allowed, False otherwise
        """
        # Check if filename contains a dot and extension is in allowed set
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def get_file_extension(self, filename):
        """
        Extract file extension from filename.
        
        Args:
            filename (str): Name of the file
            
        Returns:
            str: File extension in lowercase (e.g., 'pdf', 'docx')
        """
        # Split filename by dot and get last part as extension in lowercase
        return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    def validate_file_size(self, file):
        """
        Validate that file size is within allowed limits.
        
        Args:
            file: File object to validate
            
        Returns:
            bool: True if file size is within limit, False otherwise
        """
        # Move file pointer to end to determine file size
        file.seek(0, os.SEEK_END)
        # Get current position which is the file size
        file_size = file.tell()
        # Reset file pointer to beginning for subsequent operations
        file.seek(0)
        # Return True if file size is within limit
        return file_size <= self.max_file_size
    
    def save_file(self, file):
        """
        Save uploaded file to temporary folder with secure filename.
        
        Args:
            file: File object to save
            
        Returns:
            str: Path to saved file
            
        Raises:
            Exception: If file save operation fails
        """
        try:
            # Get current datetime
            ct = datetime.now()
            # Convert to timestamp
            ts = ct.timestamp()
            # Create unique filename with timestamp prefix and secure the filename
            filename = str(ts) + "_" + secure_filename(file.filename)
            # Build complete file path
            file_path = os.path.join(self.temp_folder, filename)
            
            # Save file to disk
            file.save(file_path)
            # Log successful save
            logging.info(f'File saved successfully: {filename}')
            # Return the file path
            return file_path
            
        except Exception as e:
            # Log error with details
            logging.error(f'Error saving file: {str(e)}')
            # Re-raise exception to caller
            raise
    

    def load_and_split_data(self, file_path):
        """
        Load document file (PDF, Word, Markdown, HTML) using Docling and split into text chunks.
        
        Args:
            file_path (str): Path to document file
            
        Returns:
            list: List of Document chunks
            
        Raises:
            ValueError: If document conversion fails or document is empty
            Exception: If unexpected error occurs
        """
        try:
            # Get file extension to determine document type
            file_extension = self.get_file_extension(file_path)
            # Log start of document conversion with file type
            logging.info(f'Starting document conversion for {file_extension.upper()} file: {file_path}')
            
            # Convert document to structured format using Docling
            result = self.converter.convert(file_path)
            
            # Check if conversion result exists
            if not result or not result.document:
                # Log error if no result
                logging.error(f'Docling conversion failed for {file_extension.upper()}: No document result')
                # Raise exception with error message
                raise ValueError(f'{file_extension.upper()} conversion failed: Unable to extract document')
            
            # Export entire document as markdown (Docling's recommended approach)
            text_content = result.document.export_to_markdown()
            
            # Validate that content is not empty
            if not text_content or text_content.strip() == '':
                # Raise exception if document is empty
                raise ValueError(f'{file_extension.upper()} conversion failed: Document is empty')
            
            # Create single document from full content with metadata
            documents = [
                Document(
                    page_content=text_content,
                    metadata={
                        "source": file_path,
                        "file_type": file_extension
                    }
                )
            ]
            
            # Log successful document creation with file type
            logging.info(f'Successfully created document from {file_extension.upper()} file')
            
            # Initialize text splitter with configured chunk size and overlap
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            # Split documents into smaller chunks for embedding
            chunks = text_splitter.split_documents(documents)
            
            # Log successful chunking
            logging.info(f'Successfully split {file_extension.upper()} into {len(chunks)} chunks')
            # Return the chunks
            return chunks
        
        except ValueError as ve:
            # Log validation errors
            logging.error(f'Validation error in load_and_split_data: {str(ve)}')
            # Re-raise validation exception
            raise
        except Exception as e:
            # Log unexpected errors
            logging.error(f'Unexpected error in load_and_split_data: {str(e)}')
            # Wrap exception with context and raise
            raise Exception(f'Failed to process document: {str(e)}')
        
    def mask_pii(self, text):
        """
        Mask personally identifiable information (PII) in text.
        
        Args:
            text (str): Text content to mask
            
        Returns:
            str: Text with PII masked
        """
        try:
            # Validate that text is not empty
            if not text or text.strip() == '':
                # Return original text if empty
                return text
            
            # Analyze text to detect PII entities (names, emails, phone numbers, etc.)
            results = self.analyzer.analyze(
                text=text,
                language="en"
            )
            
            # If no PII entities detected, return original text
            if not results:
                return text
            
            # Replace detected PII with anonymized placeholders
            masked_text = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results
            ).text
            
            # Return masked text
            return masked_text
            
        except Exception as e:
            # Log error during PII masking
            logging.error(f'Error in mask_pii: {str(e)}')
            # Return original text as fallback if masking fails
            return text
    
    def create_mask(self, chunks):
        """
        Apply PII masking to all document chunks.
        
        Args:
            chunks (list): List of Document chunks
            
        Returns:
            list: List of chunks with PII masked
        """
        try:
            # Initialize list for masked chunks
            masked_chunks = []
            # Iterate through each chunk with index
            for idx, chunk in enumerate(chunks):
                try:
                    # Mask PII in chunk content
                    masked_content = self.mask_pii(chunk.page_content)
                    
                    # Create new Document with masked content and original metadata
                    masked_chunks.append(
                        Document(
                            page_content=masked_content,
                            metadata=chunk.metadata
                        )
                    )
                except Exception as e:
                    # Log error for this chunk
                    logging.error(f'Error masking chunk {idx}: {str(e)}')
                    # Keep original chunk if masking fails
                    masked_chunks.append(chunk)
            
            # Return list of masked chunks
            return masked_chunks
            
        except Exception as e:
            # Log error in entire masking process
            logging.error(f'Error in create_mask: {str(e)}')
            # Return original chunks if entire process fails
            return chunks
    
    def embed(self, file, user_role, pwd, enable_pii_masking=True):
        """
        Main method to handle document embedding process for multiple formats.
        Supports: PDF, Word (DOCX/DOC), Markdown (MD), HTML
        
        Args:
            file: File object to embed
            user_role (str): User role for database access
            pwd (str): Password for database authentication
            enable_pii_masking (bool): Whether to enable PII masking
            
        Returns:
            bool: True if embedding successful, False otherwise
        """
        # Initialize file_path variable for cleanup in finally block
        file_path = None
        try:
            # Log start of embedding process
            logging.info(f'::::: EMBEDDING TO VECTOR DB:BEGIN:::{user_role}')
            
            # Validate that file object exists and has a filename
            if not file or not file.filename or file.filename == '':
                # Log error for missing file
                logging.error('No file provided or empty filename')
                # Return False to indicate failure
                return False
            
            # Check if file type is allowed (PDF, DOCX, DOC, MD, HTML, HTM)
            if not self.allowed_file(file.filename):
                # Log error for invalid file type
                logging.error(f'File type not allowed: {file.filename}. Supported formats: PDF, DOCX, DOC, MD, HTML, HTM')
                # Return False to indicate failure
                return False
            
            # Validate file size is within limits
            if not self.validate_file_size(file):
                # Log error for oversized file
                logging.error(f'File size exceeds maximum allowed size: {self.max_file_size} bytes')
                # Return False to indicate failure
                return False
            
            # Save file to temporary location
            file_path = self.save_file(file)
            
            # Load document and split into chunks using Docling
            chunks = self.load_and_split_data(file_path)
            
            # Validate that chunks were created
            if not chunks or len(chunks) == 0:
                # Log error for empty chunks
                logging.error('No chunks created from document')
                # Return False to indicate failure
                return False
            
            # Apply PII masking if enabled
            if enable_pii_masking:
                # Mask PII in all chunks
                logging.info("::::: MASKING IN PROCESS ::::::: BEGIN");
                chunks = self.create_mask(chunks)
                logging.info("::::: MASKING IN PROCESS ::::::: END");
            
            # Get vector database connection using user credentials
            db = get_vector_db(user_role, pwd)
            
            # Validate database connection was established
            if not db:
                # Log error for failed database connection
                logging.error('Failed to get vector database connection')
                # Return False to indicate failure
                return False
            
            # Insert chunks into vector database
            try:
                # Log start of database insertion
                logging.info(f'::::: INSERT TO VECTOR DB:BEGIN {user_role} :::::')
                # Add documents to vector database
                db.add_documents(chunks)
                # Index same chunks into Solr for BM25 keyword search
                self.solrIndexer.index_to_solr(chunks)   # <-- add this line
                # Log successful insertion
                logging.info('::::: INSERT TO VECTOR DB SUCESSFULLY:END :::::')
                
            except ProgrammingError as e:
                # Log database programming error
                logging.error(f'Database programming error: {str(e)}')
                # Check if error is permission-related
                if "row-level security" in str(e).lower() or "permission denied" in str(e).lower():
                    # Log permission error
                    logging.error('Permission denied for database operation')
                    # Return False for permission errors
                    return False
                else:
                    # Re-raise non-permission errors
                    raise
                    
            except psycopg2.errors.InsufficientPrivilege as e:
                # Log insufficient privilege error
                logging.error(f'Insufficient database privileges: {str(e)}')
                # Return False for privilege errors
                return False
                
            except OperationalError as e:
                # Log operational error
                logging.error(f'Database operational error: {str(e)}')
                # Return False for operational errors
                return False
            
            # Log successful embedding with chunk count
            logging.info(f'Successfully embedded {len(chunks)} chunks for user: {user_role}')
            # Return True to indicate success
            return True
            
        except Exception as e:
            # Log unexpected errors
            logging.error(f'Unexpected error in embed function: {str(e)}')
            # Return False for any unexpected errors
            return False
            
        finally:
            # Clean up: Remove temporary file if it exists
            if file_path and os.path.exists(file_path):
                try:
                    # Delete temporary file
                    os.remove(file_path)
                    # Log successful cleanup
                    logging.info(f'Temporary file removed: {file_path}')
                except Exception as e:
                    # Log error during cleanup
                    logging.error(f'Error removing temporary file {file_path}: {str(e)}')
    
    

# Usage example:
# embedder = DocumentEmbedder()
# 
# # Embed PDF
# success = embedder.embed(file=pdf_file, user_role='admin', pwd='password', enable_pii_masking=True)
# 
# # Embed Word document
# success = embedder.embed(file=docx_file, user_role='admin', pwd='password', enable_pii_masking=False)
# 
# # Embed Markdown
# success = embedder.embed(file=md_file, user_role='admin', pwd='password')
# 
# # Embed HTML
# success = embedder.embed(file=html_file, user_role='admin', pwd='password')