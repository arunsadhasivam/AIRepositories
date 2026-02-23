from enum import Enum
class DistanceMetric(Enum):
    """Supported distance metrics for similarity search."""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"