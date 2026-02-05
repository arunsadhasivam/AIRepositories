from enum import Enum
class EmbeddingType(Enum):
    """Available embedding models"""
    MINILM = "all-MiniLM-L6-v2"
    MPNet = "all-mpnet-base-v2"
    OPENAI = "text-embedding-3-small"