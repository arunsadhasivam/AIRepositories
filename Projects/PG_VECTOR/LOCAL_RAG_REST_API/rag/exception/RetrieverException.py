import logging

# Configure logging for production monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RetrieverException(Exception):
    """Custom exception for retriever-related errors."""
    try :
        logger.error(f"::::: RetrieverException BEGIN :::::")
    except Exception as e:
        logger.error(f"::::: RetrieverException :::::",str(e))
