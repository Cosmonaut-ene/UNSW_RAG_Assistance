# config/rag_config.py
"""
Single source of truth for all RAG-pipeline tunable parameters (E1 in SPEC.md).

Before this file existed, these parameters were hardcoded independently
across retrieve_node, HybridSearchEngine's class defaults, reranker.py,
retrieval_evaluator.py, hallucination_checker.py, safety_checker.py, etc.
-- and had already drifted apart from each other: graph_rag.py's actual
runtime values disagreed with HybridSearchEngine's own class defaults,
and evaluation/tuner_config.py's BASELINE_CONFIG claimed to "mirror
graph_rag.py's hard-coded values" while being wrong on 6 of 7 fields
(the tuning run in commit 6590ea5 updated graph_rag.py by hand but never
updated that comment/baseline -- exactly the failure mode this file
exists to close off).

Every RAG-related tunable parameter introduced from now on belongs here,
not as a new local constant in whichever module happens to need it.
"""

import json
from dataclasses import dataclass, fields, asdict
from pathlib import Path
from typing import Any, Dict

_OVERRIDES_PATH = Path(__file__).parent / "rag_config_overrides.json"


@dataclass
class RAGConfig:
    """All tunable RAG pipeline parameters in one place."""

    # --- Retrieval fusion (rag/graph_rag.py retrieve_node, rag/hybrid_search.py) ---
    # Tuned via evaluation/retrieval_tuner.py (50-trial random search + focused
    # grid + RAGAS validation, see commit 6590ea5) -- these are not guesses.
    vector_k: int = 50
    max_hybrid_results: int = 50
    min_hybrid_score: float = 50.0
    min_rag_score: float = 25.0
    min_bm25_score: float = 1.0
    rag_weight: float = 0.7
    bm25_weight: float = 0.3

    # --- HyDE search (rag/graph_rag.py retrieve_node -> rag/hyde.py) ---
    hyde_search_k: int = 10

    # --- Reranking (rag/reranker.py) ---
    reranker_top_k: int = 12
    reranker_chunk_truncation: int = 1500  # cross-encoder's ~512 token limit; chunks target 600 chars so this rarely triggers

    # --- CRAG grading (rag/retrieval_evaluator.py) ---
    crag_chunk_truncation: int = 700  # covers the ~600-char target chunk size with headroom (D1)

    # --- Hallucination faithfulness check (rag/hallucination_checker.py) ---
    faithfulness_context_truncation: int = 700  # consistent with CRAG's truncation (D3)

    # --- Safety check (ai/safety_checker.py) ---
    max_query_length: int = 10000  # spam/DoS guard, not a security judgment (C1)

    # --- Chunking (rag/text_splitter.py) -- kept in sync with CHUNK_CONFIG there ---
    target_chunk_size: int = 600
    min_chunk_size: int = 200

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RAGConfig":
        valid_keys = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid_keys})

    @classmethod
    def load(cls) -> "RAGConfig":
        """
        Load the active config: dataclass defaults above are the documented
        baseline (with tuning provenance noted inline); rag_config_overrides.json
        (if present) holds the latest tuned values, written by
        evaluation/retrieval_tuner.py after a tuning run via save_as_overrides().

        This is the single mechanism for updating production parameters --
        no more hand-copying numbers into graph_rag.py and a commit message
        as two separate, driftable steps.
        """
        config = cls()
        if _OVERRIDES_PATH.exists():
            with open(_OVERRIDES_PATH) as f:
                overrides = json.load(f)
            config = cls.from_dict({**config.as_dict(), **overrides})
        return config

    def save_as_overrides(self) -> None:
        """Persist this config as the active overrides. Call after a tuning run."""
        with open(_OVERRIDES_PATH, 'w') as f:
            json.dump(self.as_dict(), f, indent=2)
        print(f"[RAGConfig] Saved tuned config to {_OVERRIDES_PATH}")


# Module-level singleton -- runtime code imports and reads this.
RAG_CONFIG = RAGConfig.load()
