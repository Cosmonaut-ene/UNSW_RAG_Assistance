"""
Unit tests for LangGraph RAG orchestration (rag/graph_rag.py)
Focused on generate_node: it must call generate_response() directly and
must NOT re-run safety_check or query_rewrite (that used to happen inside
the old process_with_ai_pipeline()).
"""

from unittest.mock import patch, MagicMock

from rag.graph_rag import generate_node


def make_state(**overrides):
    state = {
        "query": "What is COMP9900?",
        "session_id": "test-session",
        "history": "",
        "conversation_history": [],
        "rewritten_query": "Introduce COMP9900",
        "hyde_doc": "",
        "documents": [],
        "reranked_docs": [
            {"page_content": "COMP9900 is a capstone project course.",
             "metadata": {"source": "docs/handbook.pdf"}}
        ],
        "docs_relevant": True,
        "answer": "",
        "answered": False,
        "matched_files": [],
        "fallback": False,
        "safety_blocked": False,
        "processing_steps": [],
        "generation_attempts": 0,
    }
    state.update(overrides)
    return state


class TestGenerateNode:
    """generate_node must not duplicate safety_check_node / query_rewrite_node's work"""

    @patch('ai.response_generator.generate_response')
    @patch('ai.response_generator.build_context_and_sources')
    @patch('ai.safety_checker.is_query_safe_by_gemini')
    @patch('ai.query_enhancer.rewrite_query_with_context')
    def test_generate_node_does_not_call_safety_check_again(
        self, mock_rewrite, mock_safety, mock_build_context, mock_generate
    ):
        mock_build_context.return_value = ("some context", ["handbook.pdf"])
        mock_generate.return_value = "COMP9900 is a capstone project course."

        generate_node(make_state())

        mock_safety.assert_not_called()

    @patch('ai.response_generator.generate_response')
    @patch('ai.response_generator.build_context_and_sources')
    @patch('ai.safety_checker.is_query_safe_by_gemini')
    @patch('ai.query_enhancer.rewrite_query_with_context')
    def test_generate_node_does_not_call_query_rewrite_again(
        self, mock_rewrite, mock_safety, mock_build_context, mock_generate
    ):
        mock_build_context.return_value = ("some context", ["handbook.pdf"])
        mock_generate.return_value = "COMP9900 is a capstone project course."

        generate_node(make_state())

        mock_rewrite.assert_not_called()

    @patch('ai.response_generator.generate_response')
    @patch('ai.response_generator.build_context_and_sources')
    def test_generate_node_calls_generate_response_with_rewritten_query(
        self, mock_build_context, mock_generate
    ):
        mock_build_context.return_value = ("some context", [])
        mock_generate.return_value = "answer text"

        generate_node(make_state(rewritten_query="Introduce COMP9900", history="hist"))

        mock_generate.assert_called_once_with("some context", "Introduce COMP9900", "hist")

    @patch('ai.response_generator.generate_response')
    @patch('ai.response_generator.build_context_and_sources')
    def test_generate_node_merges_matched_files(self, mock_build_context, mock_generate):
        mock_build_context.return_value = ("ctx", ["handbook.pdf", "comp9900.html"])
        mock_generate.return_value = "answer"

        result = generate_node(make_state(matched_files=["existing.pdf", "handbook.pdf"]))

        assert result["matched_files"] == ["existing.pdf", "handbook.pdf", "comp9900.html"]

    @patch('ai.response_generator.generate_response')
    @patch('ai.response_generator.build_context_and_sources')
    def test_generate_node_increments_generation_attempts(self, mock_build_context, mock_generate):
        mock_build_context.return_value = ("ctx", [])
        mock_generate.return_value = "answer"

        result = generate_node(make_state(generation_attempts=1))

        assert result["generation_attempts"] == 2

    @patch('ai.response_generator.generate_response')
    @patch('ai.response_generator.build_context_and_sources')
    def test_generate_node_sets_answered_true(self, mock_build_context, mock_generate):
        mock_build_context.return_value = ("ctx", [])
        mock_generate.return_value = "answer"

        result = generate_node(make_state())

        assert result["answered"] is True
        assert result["answer"] == "answer"
