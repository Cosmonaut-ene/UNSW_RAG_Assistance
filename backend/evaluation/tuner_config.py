"""
Retrieval tuner configuration: parameter search space, reusing the single
RAGConfig dataclass (config/rag_config.py) instead of a separate,
independently-drifting copy (E1 in SPEC.md).

This file used to define its own RetrievalConfig with a BASELINE_CONFIG
comment claiming to "mirror graph_rag.py's hard-coded values" -- which,
after the tuning run in commit 6590ea5 updated graph_rag.py by hand, was
wrong on 6 of 7 fields and nobody noticed until this file's own history
was audited. RetrievalConfig is kept as an alias purely so existing
imports elsewhere don't need renaming; BASELINE_CONFIG is now RAGConfig's
own loader, so there is exactly one place these numbers live.
"""

from typing import Dict, List, Any

from config.rag_config import RAGConfig

# Alias for backward compatibility with existing `from .tuner_config import
# RetrievalConfig` imports -- same class, not a copy.
RetrievalConfig = RAGConfig

# Default (baseline) config — loads from config/rag_config.py's single
# source of truth (dataclass defaults + rag_config_overrides.json if a
# tuning run has already applied one). Guaranteed to match what's actually
# running, because it's the same loader graph_rag.py uses.
BASELINE_CONFIG = RAGConfig.load()

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
