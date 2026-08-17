"""
Unit tests for evaluation/retrieval_tuner.py -- RetrievalRunner._hybrid_combine
must respect real rag_score values, not hardcode 100 (part of B2 in SPEC.md,
mirrors the same fix already applied in rag/hybrid_search.py for B1).
"""

from evaluation.retrieval_tuner import RetrievalRunner, RetrievalConfig, TunerOrchestrator


def make_runner() -> RetrievalRunner:
    """Build a RetrievalRunner without running __init__ (which loads the
    real vector store + BM25 index) -- _hybrid_combine is a pure method
    that only needs plain dicts."""
    return RetrievalRunner.__new__(RetrievalRunner)


def make_config(**overrides) -> RetrievalConfig:
    config = RetrievalConfig()
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


class TestHybridCombineRealScores:

    def test_respects_real_rag_score_from_run(self):
        runner = make_runner()
        config = make_config(min_hybrid_score=0.0, min_rag_score=0.0, min_bm25_score=0.0)

        rag_results = [
            {"page_content": "A relevant chunk", "metadata": {"rag_score": 62.3}},
        ]

        combined = runner._hybrid_combine(rag_results, [], config)

        assert combined[0]["metadata"]["rag_score"] == 62.3

    def test_low_real_score_gets_filtered_out(self):
        """
        Before this fix, every RAG result was hardcoded to rag_score=100,
        so it always cleared min_rag_score regardless of true relevance.
        """
        runner = make_runner()
        config = make_config(min_hybrid_score=50.0, min_rag_score=30.0, min_bm25_score=5.0, rag_weight=0.7)

        rag_results = [
            {"page_content": "A barely relevant chunk", "metadata": {"rag_score": 12.0}},
        ]

        combined = runner._hybrid_combine(rag_results, [], config)

        assert combined == []

    def test_different_scores_rank_differently(self):
        runner = make_runner()
        config = make_config(min_hybrid_score=0.0, min_rag_score=0.0, min_bm25_score=0.0)

        rag_results = [
            {"page_content": "Highly relevant chunk", "metadata": {"rag_score": 90.0}},
            {"page_content": "Weakly relevant chunk", "metadata": {"rag_score": 20.0}},
        ]

        combined = runner._hybrid_combine(rag_results, [], config)

        assert combined[0]["page_content"] == "Highly relevant chunk"
        assert combined[0]["metadata"]["hybrid_score"] > combined[1]["metadata"]["hybrid_score"]


class TestApplyBestConfig:
    """
    TunerOrchestrator.apply_best_config() is the mechanism that closes the
    loop E1 in SPEC.md requires: a tuning run's winning config gets written
    to config/rag_config_overrides.json directly, not hand-copied into
    graph_rag.py and a commit message as two separate, driftable steps.
    """

    def test_applies_top_ranked_candidate_by_default(self, tmp_path, monkeypatch):
        overrides_path = tmp_path / "rag_config_overrides.json"
        monkeypatch.setattr("config.rag_config._OVERRIDES_PATH", overrides_path)

        orchestrator = TunerOrchestrator(results_dir=str(tmp_path))
        validation_output = {
            "candidates": [
                {"config": RetrievalConfig(vector_k=77).as_dict(), "context_recall": 0.30},
                {"config": RetrievalConfig(vector_k=10).as_dict(), "context_recall": 0.10},
            ]
        }

        applied = orchestrator.apply_best_config(validation_output)

        assert applied.vector_k == 77
        assert overrides_path.exists()

    def test_applies_specified_rank(self, tmp_path, monkeypatch):
        overrides_path = tmp_path / "rag_config_overrides.json"
        monkeypatch.setattr("config.rag_config._OVERRIDES_PATH", overrides_path)

        orchestrator = TunerOrchestrator(results_dir=str(tmp_path))
        validation_output = {
            "candidates": [
                {"config": RetrievalConfig(vector_k=77).as_dict(), "context_recall": 0.30},
                {"config": RetrievalConfig(vector_k=10).as_dict(), "context_recall": 0.10},
            ]
        }

        applied = orchestrator.apply_best_config(validation_output, rank=2)

        assert applied.vector_k == 10

    def test_invalid_rank_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr("config.rag_config._OVERRIDES_PATH", tmp_path / "overrides.json")

        orchestrator = TunerOrchestrator(results_dir=str(tmp_path))
        validation_output = {"candidates": [{"config": RetrievalConfig().as_dict(), "context_recall": 0.1}]}

        try:
            orchestrator.apply_best_config(validation_output, rank=5)
            assert False, "expected ValueError"
        except ValueError:
            pass

    def test_no_saved_results_raises_when_none_provided(self, tmp_path, monkeypatch):
        monkeypatch.setattr("config.rag_config._OVERRIDES_PATH", tmp_path / "overrides.json")

        orchestrator = TunerOrchestrator(results_dir=str(tmp_path))

        try:
            orchestrator.apply_best_config()
            assert False, "expected RuntimeError"
        except RuntimeError:
            pass
