"""
Retrieval tuner configuration: parameter search space and RetrievalConfig dataclass.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class RetrievalConfig:
    """All tunable retrieval parameters in one place."""
    vector_k: int = 20
    max_hybrid_results: int = 30
    min_hybrid_score: float = 70.0
    min_rag_score: float = 25.0
    min_bm25_score: float = 3.0
    rag_weight: float = 0.6
    reranker_top_k: int = 7

    def as_dict(self) -> Dict[str, Any]:
        return {
            "vector_k": self.vector_k,
            "max_hybrid_results": self.max_hybrid_results,
            "min_hybrid_score": self.min_hybrid_score,
            "min_rag_score": self.min_rag_score,
            "min_bm25_score": self.min_bm25_score,
            "rag_weight": self.rag_weight,
            "reranker_top_k": self.reranker_top_k,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RetrievalConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# Default (baseline) config — mirrors current graph_rag.py hard-coded values
BASELINE_CONFIG = RetrievalConfig()

# Parameter search space for random / grid search
SEARCH_SPACE: Dict[str, List[Any]] = {
    "vector_k":           [20, 30, 40, 50],
    "max_hybrid_results": [30, 40, 50],
    "min_hybrid_score":   [30.0, 50.0, 70.0],
    "min_rag_score":      [15.0, 20.0, 25.0],
    "min_bm25_score":     [1.0, 3.0],
    "rag_weight":         [0.5, 0.6, 0.7],
    "reranker_top_k":     [7, 10, 12],
}

# Tuner run settings
TUNER_SETTINGS: Dict[str, Any] = {
    "n_random": 50,          # Number of random search trials
    "top_k_focused": 5,      # Top configs to use for focused grid
    "top_k_validate": 5,     # Top configs to validate with full RAGAS
    "random_seed": 42,
    "proxy_weights": {
        "gt_recall": 0.5,    # Ground-truth keyword recall weight
        "kw_hits": 0.3,      # expected_context_keywords hit rate weight
        "richness": 0.2,     # Long-chunk (≥500 chars) ratio weight
    },
    "rich_chunk_min_len": 500,
}
