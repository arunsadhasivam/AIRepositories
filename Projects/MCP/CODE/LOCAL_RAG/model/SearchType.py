from enum import Enum
class SearchType(Enum):
    """Available search strategies"""
    COSINE = "cosine"
    HYBRID = "hybrid"
    RERANKER = "reranker"