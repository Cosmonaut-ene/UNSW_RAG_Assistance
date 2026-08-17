"""
Unit tests for AI Query Enhancer module (C3 in SPEC.md)

Rewritten for the merged design: query_rewrite and hyde_generate used to be
two separate LLM calls; analyze_query_with_context() now does both in one
structured call, returning {"intent", "rewritten_query", "hypothetical_document"}
instead of a bare rewritten-query string.
"""

import json
from unittest.mock import patch, MagicMock

from ai.query_enhancer import analyze_query_with_context


def mock_analysis_response(mock_get_genai_model, intent="REWRITE", rewritten_query="", hypothetical_document=""):
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = json.dumps({
        "intent": intent,
        "rewritten_query": rewritten_query,
        "hypothetical_document": hypothetical_document,
    })
    mock_get_genai_model.return_value = mock_model
    return mock_model


class TestAnalyzeQueryWithContext:
    """Core merged behavior: one call produces both rewrite and HyDE doc"""

    @patch('ai.query_enhancer.get_genai_model')
    def test_rewrite_intent_returns_rewritten_query_and_hyde_doc(self, mock_get_genai_model):
        mock_analysis_response(
            mock_get_genai_model,
            intent="REWRITE",
            rewritten_query="COMP9900 overview description prerequisites",
            hypothetical_document="COMP9900 is a capstone project course covering software development practices.",
        )

        result = analyze_query_with_context("What is COMP9900", [])

        assert result["intent"] == "REWRITE"
        assert result["rewritten_query"] == "COMP9900 overview description prerequisites"
        assert result["hypothetical_document"] == "COMP9900 is a capstone project course covering software development practices."

    @patch('ai.query_enhancer.get_genai_model')
    def test_navigation_intent_leaves_rewrite_and_hyde_empty(self, mock_get_genai_model):
        mock_analysis_response(mock_get_genai_model, intent="NAVIGATION", rewritten_query="", hypothetical_document="")

        result = analyze_query_with_context("Where is J17?", [])

        assert result["intent"] == "NAVIGATION"
        assert result["rewritten_query"] == ""
        assert result["hypothetical_document"] == ""

    @patch('ai.query_enhancer.get_genai_model')
    def test_hypothetical_document_forced_empty_for_navigation_even_if_model_returns_one(self, mock_get_genai_model):
        """Defensive: even if the model doesn't follow the 'leave empty' instruction, we discard it"""
        mock_analysis_response(
            mock_get_genai_model,
            intent="NAVIGATION",
            rewritten_query="",
            hypothetical_document="J17 is the CSE building.",
        )

        result = analyze_query_with_context("Where is J17?", [])

        assert result["hypothetical_document"] == ""

    @patch('ai.query_enhancer.get_genai_model')
    def test_single_llm_call_per_query(self, mock_get_genai_model):
        """The whole point of C3: one call, not two (query_rewrite + hyde_generate)"""
        mock_model = mock_analysis_response(mock_get_genai_model, rewritten_query="COMP9900 overview")

        analyze_query_with_context("What is COMP9900?", [])

        assert mock_model.generate_content.call_count == 1

    @patch('ai.query_enhancer.get_genai_model')
    def test_uses_structured_output_schema(self, mock_get_genai_model):
        mock_model = mock_analysis_response(mock_get_genai_model, rewritten_query="COMP9900 overview")

        analyze_query_with_context("What is COMP9900?", [])

        _, kwargs = mock_model.generate_content.call_args
        gen_config = kwargs["generation_config"]
        assert gen_config["response_mime_type"] == "application/json"
        assert "response_schema" in gen_config


class TestAnalyzeQueryWithContextEdgeCases:

    @patch('ai.query_enhancer.get_genai_model')
    def test_empty_query_no_llm_call(self, mock_get_genai_model):
        mock_model = MagicMock()
        mock_get_genai_model.return_value = mock_model

        result = analyze_query_with_context("", [])

        assert result["intent"] == "REWRITE"
        assert result["rewritten_query"] == ""
        mock_model.generate_content.assert_not_called()

    @patch('ai.query_enhancer.get_genai_model')
    def test_none_query_no_llm_call(self, mock_get_genai_model):
        mock_model = MagicMock()
        mock_get_genai_model.return_value = mock_model

        result = analyze_query_with_context(None, [])

        assert result["intent"] == "REWRITE"
        mock_model.generate_content.assert_not_called()

    @patch('ai.query_enhancer.get_genai_model')
    def test_whitespace_only_query_no_llm_call(self, mock_get_genai_model):
        mock_model = MagicMock()
        mock_get_genai_model.return_value = mock_model

        result = analyze_query_with_context("   \t\n   ", [])

        assert result["intent"] == "REWRITE"
        mock_model.generate_content.assert_not_called()

    @patch('ai.query_enhancer.get_genai_model')
    def test_none_conversation_history(self, mock_get_genai_model):
        mock_analysis_response(mock_get_genai_model, rewritten_query="COMP9900 overview")

        result = analyze_query_with_context("What is COMP9900?", None)

        assert result["rewritten_query"] == "COMP9900 overview"

    @patch('ai.query_enhancer.get_genai_model')
    def test_malformed_conversation_history_does_not_crash(self, mock_get_genai_model):
        mock_analysis_response(mock_get_genai_model, rewritten_query="COMP9900 overview")

        malformed_history = [
            {"question": "What is COMP9900?"},  # missing answer
            {"answer": "Some answer"},  # missing question
            {"question": None, "answer": None},
            "invalid_format",
        ]

        result = analyze_query_with_context("What is COMP9900?", malformed_history)

        assert result["rewritten_query"] == "COMP9900 overview"

    @patch('ai.query_enhancer.get_genai_model')
    def test_api_exception_defaults_to_rewrite_with_original_query(self, mock_get_genai_model):
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_get_genai_model.return_value = mock_model

        result = analyze_query_with_context("What is COMP9900?", [])

        assert result["intent"] == "REWRITE"
        assert result["rewritten_query"] == "What is COMP9900?"
        assert result["hypothetical_document"] == ""

    @patch('ai.query_enhancer.get_genai_model')
    def test_malformed_json_response_defaults_to_rewrite(self, mock_get_genai_model):
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "not valid json"
        mock_get_genai_model.return_value = mock_model

        result = analyze_query_with_context("What is COMP9900?", [])

        assert result["intent"] == "REWRITE"
        assert result["rewritten_query"] == "What is COMP9900?"

    @patch('ai.query_enhancer.get_genai_model')
    def test_unexpected_intent_value_defaults_to_rewrite(self, mock_get_genai_model):
        mock_analysis_response(mock_get_genai_model, intent="MAYBE", rewritten_query="COMP9900 overview")

        result = analyze_query_with_context("What is COMP9900?", [])

        assert result["intent"] == "REWRITE"

    @patch('ai.query_enhancer.get_genai_model')
    def test_empty_rewritten_query_falls_back_to_original(self, mock_get_genai_model):
        mock_analysis_response(mock_get_genai_model, intent="REWRITE", rewritten_query="")

        result = analyze_query_with_context("What is COMP9900?", [])

        assert result["rewritten_query"] == "What is COMP9900?"


class TestAnalyzeQueryWithContextConversationHistory:

    @patch('ai.query_enhancer.get_genai_model')
    def test_conversation_history_included_in_prompt(self, mock_get_genai_model):
        mock_model = mock_analysis_response(mock_get_genai_model, rewritten_query="COMP9900 assessment")

        conversation_history = [
            {"question": "What is COMP9900?", "answer": "COMP9900 is a capstone project course."},
        ]

        analyze_query_with_context("What about the assessment?", conversation_history)

        prompt_sent = mock_model.generate_content.call_args[0][0]
        assert "COMP9900" in prompt_sent
        assert "capstone project" in prompt_sent


class TestAnalyzeQueryWithContextHydePromptConstraints:
    """
    Carried over from the pre-C3 HyDE-specific tests: the hypothetical
    document instructions must not ask the model to invent course codes
    (A3 in SPEC.md), and must still ask for document-style language.
    """

    @patch('ai.query_enhancer.get_genai_model')
    def test_prompt_forbids_inventing_identifiers(self, mock_get_genai_model):
        mock_model = mock_analysis_response(mock_get_genai_model, rewritten_query="COMP9900 overview")

        analyze_query_with_context("What is COMP9900?", [])

        prompt_sent = mock_model.generate_content.call_args[0][0]
        assert "do not invent" in prompt_sent.lower()

    @patch('ai.query_enhancer.get_genai_model')
    def test_prompt_asks_for_document_style_language(self, mock_get_genai_model):
        mock_model = mock_analysis_response(mock_get_genai_model, rewritten_query="COMP9900 overview")

        analyze_query_with_context("What is COMP9900?", [])

        prompt_sent = mock_model.generate_content.call_args[0][0]
        assert "unsw documentation" in prompt_sent.lower()
