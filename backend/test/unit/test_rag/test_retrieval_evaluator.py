"""
Unit tests for CRAG document grading (rag/retrieval_evaluator.py) -- D1 in
SPEC.md.

The old implementation only evaluated the top 5 of up to 12 reranked
documents, yet approved all 12 regardless of the verdict (all-or-nothing,
not real filtering). This rewrite grades every document individually via a
single structured call and keeps only the ones judged relevant.
"""

import json
from unittest.mock import patch, MagicMock

from rag.retrieval_evaluator import grade_documents
from config.rag_config import RAG_CONFIG


def make_docs(n, prefix="Document"):
    return [{"page_content": f"{prefix} {i} content", "metadata": {"source": f"doc{i}.pdf"}} for i in range(n)]


def mock_relevance_response(mock_get_model, relevance: list):
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = json.dumps({"relevance": relevance})
    mock_get_model.return_value = mock_model
    return mock_model


class TestGradeDocumentsCoreBehavior:

    def test_no_documents_returns_incorrect(self):
        grade, filtered = grade_documents("What is COMP9900?", [])

        assert grade == "INCORRECT"
        assert filtered == []

    @patch('ai.llm_client.get_genai_model')
    def test_all_relevant_keeps_all(self, mock_get_model):
        docs = make_docs(3)
        mock_relevance_response(mock_get_model, [True, True, True])

        grade, filtered = grade_documents("What is COMP9900?", docs)

        assert grade == "CORRECT"
        assert len(filtered) == 3

    @patch('ai.llm_client.get_genai_model')
    def test_mixed_relevance_keeps_only_relevant(self, mock_get_model):
        docs = make_docs(4)
        mock_relevance_response(mock_get_model, [True, False, True, False])

        grade, filtered = grade_documents("What is COMP9900?", docs)

        assert grade == "CORRECT"
        assert len(filtered) == 2
        assert filtered[0]["page_content"] == "Document 0 content"
        assert filtered[1]["page_content"] == "Document 2 content"

    @patch('ai.llm_client.get_genai_model')
    def test_all_irrelevant_returns_incorrect_and_empty(self, mock_get_model):
        docs = make_docs(3)
        mock_relevance_response(mock_get_model, [False, False, False])

        grade, filtered = grade_documents("What is COMP9900?", docs)

        assert grade == "INCORRECT"
        assert filtered == []


class TestGradeDocumentsCoversAllDocuments:
    """The core bug being fixed: must not silently only look at the first 5"""

    @patch('ai.llm_client.get_genai_model')
    def test_grades_all_twelve_documents_not_just_five(self, mock_get_model):
        docs = make_docs(12)
        # Only the last document (index 11) is relevant -- would be
        # invisible to the old implementation, which only ever looked at
        # documents[:5]
        relevance = [False] * 11 + [True]
        mock_relevance_response(mock_get_model, relevance)

        grade, filtered = grade_documents("What is COMP9900?", docs)

        assert grade == "CORRECT"
        assert len(filtered) == 1
        assert filtered[0]["page_content"] == "Document 11 content"

    @patch('ai.llm_client.get_genai_model')
    def test_prompt_includes_every_document(self, mock_get_model):
        docs = make_docs(12)
        mock_model = mock_relevance_response(mock_get_model, [True] * 12)

        grade_documents("What is COMP9900?", docs)

        prompt_sent = mock_model.generate_content.call_args[0][0]
        for i in range(12):
            assert f"Document {i} content"[:RAG_CONFIG.crag_chunk_truncation] in prompt_sent


class TestGradeDocumentsStructuredOutput:

    @patch('ai.llm_client.get_genai_model')
    def test_uses_response_schema(self, mock_get_model):
        docs = make_docs(2)
        mock_model = mock_relevance_response(mock_get_model, [True, True])

        grade_documents("What is COMP9900?", docs)

        _, kwargs = mock_model.generate_content.call_args
        gen_config = kwargs["generation_config"]
        assert gen_config["response_mime_type"] == "application/json"
        assert "response_schema" in gen_config

    @patch('ai.llm_client.get_genai_model')
    def test_mismatched_relevance_array_length_does_not_crash(self, mock_get_model):
        """Model returns fewer booleans than documents -- must pad, not crash or misalign"""
        docs = make_docs(5)
        mock_relevance_response(mock_get_model, [True, True])  # only 2, not 5

        grade, filtered = grade_documents("What is COMP9900?", docs)

        # Should not raise; missing entries treated as not relevant
        assert len(filtered) <= 2

    @patch('ai.llm_client.get_genai_model')
    def test_oversized_relevance_array_truncated(self, mock_get_model):
        docs = make_docs(2)
        mock_relevance_response(mock_get_model, [True, True, True, True])  # 4, not 2

        grade, filtered = grade_documents("What is COMP9900?", docs)

        assert len(filtered) == 2


class TestGradeDocumentsErrorHandling:

    @patch('ai.llm_client.get_genai_model')
    def test_api_exception_defaults_correct_fail_open(self, mock_get_model):
        docs = make_docs(3)
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_get_model.return_value = mock_model

        grade, filtered = grade_documents("What is COMP9900?", docs)

        assert grade == "CORRECT"
        assert filtered == docs

    @patch('ai.llm_client.get_genai_model')
    def test_malformed_json_defaults_correct_fail_open(self, mock_get_model):
        docs = make_docs(3)
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "not valid json"
        mock_get_model.return_value = mock_model

        grade, filtered = grade_documents("What is COMP9900?", docs)

        assert grade == "CORRECT"
        assert filtered == docs
