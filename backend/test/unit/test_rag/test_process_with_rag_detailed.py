"""
Unit tests for rag.process_with_rag_detailed() -- must thread real similarity
scores through into each result's metadata (B1 in SPEC.md), not silently
drop them the way search_similar_documents() does.
"""

from unittest.mock import patch, MagicMock

from rag import process_with_rag_detailed


class FakeDoc:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


class TestProcessWithRagDetailedScores:

    @patch('rag.search_documents_with_scores')
    def test_attaches_normalized_rag_score_to_each_result(self, mock_scored_search):
        mock_scored_search.return_value = [
            (FakeDoc("relevant content", {"source": "a.pdf"}), 0.0),   # distance 0 -> score 100
            (FakeDoc("less relevant content", {"source": "b.pdf"}), 2.0),  # distance 2 -> score 0
        ]

        result = process_with_rag_detailed("What is COMP9900?")

        scores = [doc["metadata"]["rag_score"] for doc in result["search_results"]]
        assert scores == [100.0, 0.0]

    @patch('rag.search_documents_with_scores')
    def test_uses_search_documents_with_scores_not_score_less_search(self, mock_scored_search):
        mock_scored_search.return_value = []

        process_with_rag_detailed("What is COMP9900?")

        mock_scored_search.assert_called_once()

    @patch('rag.search_documents_with_scores')
    def test_empty_results_handled(self, mock_scored_search):
        mock_scored_search.return_value = []

        result = process_with_rag_detailed("What is COMP9900?")

        assert result["search_results"] == []
