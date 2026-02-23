import logging

# Configure logging for production monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
class ChainException(Exception):
    """Custom exception for ChainException errors."""
    try :
        logger.error(f"::::: ChainException :BEGIN :::::")
    except Exception as e:
        logger.error(f"::::: ChainException :::::",str(e))
