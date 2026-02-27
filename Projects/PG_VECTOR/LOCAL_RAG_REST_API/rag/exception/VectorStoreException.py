import logging

# Configure logging for production monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
class VectorStoreException(Exception):
    """Vector Store exception for retriever-related errors."""
    def __init__(self, message: str, cause: Exception = None):
        # Call parent Exception constructor with message
        super().__init__(message)
        # Store original cause for chaining
        self.cause = cause
        # Log error when exception is created
        logger.error(f"VectorStoreException: {message}" + (f" | Cause: {str(cause)}" if cause else ""))
