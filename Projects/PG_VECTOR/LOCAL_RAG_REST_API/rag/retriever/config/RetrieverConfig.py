
from dataclasses import dataclass


@dataclass
class RetrieverConfig:
    """Configuration for hybrid retriever weights and parameters."""
    vector_weight: float = 0.5
    sparse_weight: float = 0.5
    min_score_threshold: float = 0.0
    normalize_scores: bool = True
    top_k:int=5
    
    def __post_init__(self):
        """Validate configuration."""
        if not 0 <= self.vector_weight <= 1:
            raise ValueError("vector_weight must be between 0 and 1")
        if not 0 <= self.sparse_weight <= 1:
            raise ValueError("sparse_weight must be between 0 and 1")