"""
Unit tests for config/rag_config.py -- the single source of truth for all
RAG-pipeline tunable parameters (E1 in SPEC.md).
"""

import json

from config.rag_config import RAGConfig


class TestRAGConfigDefaults:

    def test_defaults_match_documented_tuned_values(self):
        """
        These specific values came from evaluation/retrieval_tuner.py's
        50-trial random search + focused grid + RAGAS validation (commit
        6590ea5) -- not guesses. Pinning them here means any accidental
        change to the dataclass defaults is caught by a test, not just
        noticed (or not) in a diff.
        """
        config = RAGConfig()

        assert config.vector_k == 50
        assert config.max_hybrid_results == 50
        assert config.min_hybrid_score == 50.0
        assert config.min_rag_score == 25.0
        assert config.min_bm25_score == 1.0
        assert config.rag_weight == 0.7
        assert config.reranker_top_k == 12


class TestRAGConfigSerialization:

    def test_as_dict_round_trips_through_from_dict(self):
        config = RAGConfig(vector_k=99, rag_weight=0.5)

        restored = RAGConfig.from_dict(config.as_dict())

        assert restored == config

    def test_from_dict_ignores_unknown_keys(self):
        """A dict with extra keys (e.g. from an old/newer schema) must not crash construction"""
        config = RAGConfig.from_dict({"vector_k": 30, "some_future_field": "ignored"})

        assert config.vector_k == 30

    def test_from_dict_partial_uses_remaining_defaults(self):
        config = RAGConfig.from_dict({"rag_weight": 0.9})

        assert config.rag_weight == 0.9
        assert config.vector_k == RAGConfig().vector_k


class TestRAGConfigLoadAndOverrides:

    def test_load_without_overrides_file_returns_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr("config.rag_config._OVERRIDES_PATH", tmp_path / "nonexistent.json")

        config = RAGConfig.load()

        assert config == RAGConfig()

    def test_save_as_overrides_then_load_reflects_tuned_values(self, tmp_path, monkeypatch):
        overrides_path = tmp_path / "rag_config_overrides.json"
        monkeypatch.setattr("config.rag_config._OVERRIDES_PATH", overrides_path)

        tuned = RAGConfig(vector_k=80, rag_weight=0.85)
        tuned.save_as_overrides()

        assert overrides_path.exists()
        loaded = RAGConfig.load()
        assert loaded.vector_k == 80
        assert loaded.rag_weight == 0.85

    def test_save_as_overrides_writes_valid_json(self, tmp_path, monkeypatch):
        overrides_path = tmp_path / "rag_config_overrides.json"
        monkeypatch.setattr("config.rag_config._OVERRIDES_PATH", overrides_path)

        RAGConfig(vector_k=42).save_as_overrides()

        with open(overrides_path) as f:
            data = json.load(f)
        assert data["vector_k"] == 42

    def test_partial_overrides_file_fills_remaining_from_defaults(self, tmp_path, monkeypatch):
        """A hand-edited or older overrides file with only some fields must not lose the rest"""
        overrides_path = tmp_path / "rag_config_overrides.json"
        overrides_path.write_text(json.dumps({"rag_weight": 0.55}))
        monkeypatch.setattr("config.rag_config._OVERRIDES_PATH", overrides_path)

        config = RAGConfig.load()

        assert config.rag_weight == 0.55
        assert config.vector_k == RAGConfig().vector_k
