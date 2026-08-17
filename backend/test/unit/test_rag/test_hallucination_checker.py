"""
Unit tests for rag/hallucination_checker.py (D3 in SPEC.md)

Replaces the old keyword-scan hallucination_check_node, which only caught
the model admitting "I don't know" -- confident fabrication (wrong course
code, invented prerequisite) sailed straight through undetected.
"""

import json
from unittest.mock import patch, MagicMock

from rag.hallucination_checker import validate_citations, check_faithfulness


class TestValidateCitations:

    def test_valid_citation_passes(self):
        answer = "COMP9900 is a capstone project.\n\n📚 Sources: [Info Tech Project](https://www.handbook.unsw.edu.au/postgraduate/courses/2025/COMP9900)"
        matched_files = ["COMP9900"]

        valid, missing = validate_citations(answer, matched_files)

        assert valid is True
        assert missing is False

    def test_fabricated_citation_fails(self):
        """Citing a document that was never actually retrieved is itself a hallucination"""
        answer = "COMP9999 is a great course.\n\n📚 Sources: [Fake Course](https://www.handbook.unsw.edu.au/postgraduate/courses/2025/COMP9999)"
        matched_files = ["COMP9900"]  # COMP9999 was never retrieved

        valid, missing = validate_citations(answer, matched_files)

        assert valid is False

    def test_missing_citation_when_context_was_used(self):
        answer = "COMP9900 is a capstone project course with no sources listed."
        matched_files = ["COMP9900"]

        valid, missing = validate_citations(answer, matched_files)

        assert missing is True

    def test_no_citation_needed_when_no_context_used(self):
        """Fallback-style answers with no matched_files shouldn't be flagged for missing citations"""
        answer = "I can help you navigate campus!"
        matched_files = []

        valid, missing = validate_citations(answer, matched_files)

        assert valid is True
        assert missing is False

    def test_multiple_citations_all_valid(self):
        answer = (
            "Both courses are relevant.\n\n"
            "📚 Sources: [Course A](https://www.handbook.unsw.edu.au/postgraduate/courses/2025/COMP9900), "
            "[Course B](https://www.handbook.unsw.edu.au/postgraduate/courses/2025/COMP9021)"
        )
        matched_files = ["COMP9900", "COMP9021"]

        valid, missing = validate_citations(answer, matched_files)

        assert valid is True

    def test_multiple_citations_one_fabricated(self):
        answer = (
            "📚 Sources: [Course A](https://www.handbook.unsw.edu.au/postgraduate/courses/2025/COMP9900), "
            "[Fake](https://www.handbook.unsw.edu.au/postgraduate/courses/2025/FAKE999)"
        )
        matched_files = ["COMP9900"]

        valid, missing = validate_citations(answer, matched_files)

        assert valid is False

    def test_pdf_source_citation(self):
        answer = "See the handbook.\n\n📚 Sources: [UNSW Magic Club](/docs/magic.pdf)"
        matched_files = ["magic.pdf"]

        valid, missing = validate_citations(answer, matched_files)

        assert valid is True

    def test_case_insensitive_matching(self):
        answer = "📚 Sources: [Course](https://www.handbook.unsw.edu.au/postgraduate/courses/2025/comp9900)"
        matched_files = ["COMP9900"]

        valid, missing = validate_citations(answer, matched_files)

        assert valid is True


class TestCheckFaithfulness:

    def test_empty_answer_not_faithful(self):
        result = check_faithfulness("", [{"page_content": "some context"}])

        assert result["faithful"] is False

    def test_insufficient_context_sentinel_not_faithful_no_llm_call(self):
        with patch('ai.llm_client.get_genai_model') as mock_get_model:
            result = check_faithfulness("INSUFFICIENT_CONTEXT", [{"page_content": "some context"}])

            assert result["faithful"] is False
            mock_get_model.assert_not_called()

    def test_no_context_docs_not_faithful(self):
        result = check_faithfulness("COMP9900 is a great course.", [])

        assert result["faithful"] is False

    @patch('ai.llm_client.get_genai_model')
    def test_faithful_answer_passes(self, mock_get_model):
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = json.dumps({
            "faithful": True,
            "unsupported_claims": [],
        })
        mock_get_model.return_value = mock_model

        result = check_faithfulness(
            "COMP9900 is a capstone project course.",
            [{"page_content": "COMP9900 is a capstone project course for final year students."}],
        )

        assert result["faithful"] is True
        assert result["unsupported_claims"] == []

    @patch('ai.llm_client.get_genai_model')
    def test_context_not_truncated(self, mock_get_model):
        """
        Must see exactly what generate_node saw (ai/response_generator.py
        build_context_and_sources doesn't truncate either) -- a live
        30-query RAGAS run found answers flagged unfaithful purely because
        this check only saw a 700-char prefix of docs that commonly run
        1000-1800 chars, missing claims genuinely grounded past that cutoff.
        """
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = json.dumps({"faithful": True, "unsupported_claims": []})
        mock_get_model.return_value = mock_model

        long_content = "A" * 500 + "COMP9900 has a group project component." + "B" * 500
        check_faithfulness("The course has a group project component.", [{"page_content": long_content}])

        prompt_arg = mock_model.generate_content.call_args[0][0]
        assert "COMP9900 has a group project component." in prompt_arg
        assert prompt_arg.count("A") >= 500 and prompt_arg.count("B") >= 500

    @patch('ai.llm_client.get_genai_model')
    def test_unfaithful_answer_lists_unsupported_claims(self, mock_get_model):
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = json.dumps({
            "faithful": False,
            "unsupported_claims": ["COMP9900 requires COMP9999 as a prerequisite"],
        })
        mock_get_model.return_value = mock_model

        result = check_faithfulness(
            "COMP9900 requires COMP9999 as a prerequisite.",
            [{"page_content": "COMP9900 is a capstone project course. No prerequisites listed."}],
        )

        assert result["faithful"] is False
        assert len(result["unsupported_claims"]) == 1

    @patch('ai.llm_client.get_genai_model')
    def test_uses_structured_output_schema(self, mock_get_model):
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = json.dumps({"faithful": True, "unsupported_claims": []})
        mock_get_model.return_value = mock_model

        check_faithfulness("answer", [{"page_content": "context"}])

        _, kwargs = mock_model.generate_content.call_args
        gen_config = kwargs["generation_config"]
        assert gen_config["response_mime_type"] == "application/json"
        assert "response_schema" in gen_config

    @patch('ai.llm_client.get_genai_model')
    def test_api_exception_defaults_faithful_fail_open(self, mock_get_model):
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_get_model.return_value = mock_model

        result = check_faithfulness("COMP9900 is a course.", [{"page_content": "context"}])

        assert result["faithful"] is True

    @patch('ai.llm_client.get_genai_model')
    def test_malformed_json_defaults_faithful_fail_open(self, mock_get_model):
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "not valid json"
        mock_get_model.return_value = mock_model

        result = check_faithfulness("COMP9900 is a course.", [{"page_content": "context"}])

        assert result["faithful"] is True
