"""
Unit tests for LangGraph RAG orchestration (rag/graph_rag.py)
Focused on generate_node: it must call generate_response() directly and
must NOT re-run safety_check or query_rewrite (that used to happen inside
the old process_with_ai_pipeline()).
"""

from unittest.mock import patch, MagicMock

from rag.graph_rag import (
    generate_node,
    query_rewrite_node,
    route_after_rewrite,
    grade_documents_node,
    route_after_grading,
    hallucination_check_node,
    fallback_node,
    route_after_hallucination_check,
)


def make_state(**overrides):
    state = {
        "query": "What is COMP9900?",
        "session_id": "test-session",
        "history": "",
        "conversation_history": [],
        "rewritten_query": "Introduce COMP9900",
        "hyde_doc": "",
        "query_intent": "REWRITE",
        "documents": [],
        "reranked_docs": [
            {"page_content": "COMP9900 is a capstone project course.",
             "metadata": {"source": "docs/handbook.pdf"}}
        ],
        "fallback_reason": "",
        "answer": "",
        "answered": False,
        "matched_files": [],
        "hallucination_detected": False,
        "fallback_used": False,
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
    @patch('ai.query_enhancer.analyze_query_with_context')
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
    @patch('ai.query_enhancer.analyze_query_with_context')
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


class TestQueryRewriteNode:
    """
    query_rewrite_node now produces rewritten_query, hyde_doc, and
    query_intent all from one call to analyze_query_with_context() (C3 in
    SPEC.md) -- previously hyde_doc came from a separate hyde_generate node.
    """

    @patch('ai.query_enhancer.analyze_query_with_context')
    def test_populates_rewritten_query_hyde_doc_and_intent_from_single_call(self, mock_analyze):
        mock_analyze.return_value = {
            "intent": "REWRITE",
            "rewritten_query": "Introduce COMP9900",
            "hypothetical_document": "COMP9900 is a capstone project course.",
        }

        result = query_rewrite_node(make_state())

        assert result["rewritten_query"] == "Introduce COMP9900"
        assert result["hyde_doc"] == "COMP9900 is a capstone project course."
        assert result["query_intent"] == "REWRITE"
        assert result["fallback_reason"] == ""
        mock_analyze.assert_called_once()

    @patch('ai.query_enhancer.analyze_query_with_context')
    def test_navigation_intent_passed_through(self, mock_analyze):
        mock_analyze.return_value = {
            "intent": "NAVIGATION",
            "rewritten_query": "",
            "hypothetical_document": "",
        }

        result = query_rewrite_node(make_state(query="Where is J17?"))

        assert result["query_intent"] == "NAVIGATION"
        assert result["hyde_doc"] == ""
        assert result["fallback_reason"] == "navigation"


class TestRouteAfterRewrite:
    """Routing now reads the structured query_intent field, not a magic string"""

    def test_navigation_intent_routes_to_fallback(self):
        assert route_after_rewrite(make_state(query_intent="NAVIGATION")) == "fallback"

    def test_rewrite_intent_routes_to_retrieve(self):
        assert route_after_rewrite(make_state(query_intent="REWRITE")) == "retrieve"

    def test_missing_intent_defaults_to_retrieve(self):
        """Should never silently misroute to fallback just because the field is absent"""
        state = make_state()
        del state["query_intent"]
        assert route_after_rewrite(state) == "retrieve"


class TestGradeDocumentsNode:
    """
    grade_documents_node now filters reranked_docs in place -- no separate
    docs_relevant flag (D1 in SPEC.md).
    """

    @patch('rag.retrieval_evaluator.grade_documents')
    def test_correct_grade_keeps_filtered_docs(self, mock_grade):
        filtered = [{"page_content": "relevant chunk", "metadata": {}}]
        mock_grade.return_value = ("CORRECT", filtered)

        result = grade_documents_node(make_state())

        assert result["reranked_docs"] == filtered
        assert "crag_incorrect" not in result["processing_steps"]
        assert "fallback_reason" not in result

    @patch('rag.retrieval_evaluator.grade_documents')
    def test_incorrect_grade_results_in_empty_docs(self, mock_grade):
        mock_grade.return_value = ("INCORRECT", [])

        result = grade_documents_node(make_state())

        assert result["reranked_docs"] == []
        assert "crag_incorrect" in result["processing_steps"]
        assert result["fallback_reason"] == "no_relevant_docs"


class TestRouteAfterGrading:
    """Routing reads reranked_docs directly -- empty means nothing survived grading"""

    def test_empty_reranked_docs_routes_to_fallback(self):
        assert route_after_grading(make_state(reranked_docs=[])) == "fallback"

    def test_nonempty_reranked_docs_routes_to_generate(self):
        docs = [{"page_content": "a", "metadata": {}}]
        assert route_after_grading(make_state(reranked_docs=docs)) == "generate"


class TestHallucinationCheckNode:
    """
    hallucination_check_node now sets hallucination_detected (not the old
    overloaded fallback field), based on validate_citations() +
    check_faithfulness() instead of scanning for "I don't know" phrases (D3).
    """

    @patch('rag.hallucination_checker.check_faithfulness')
    @patch('rag.hallucination_checker.validate_citations')
    def test_faithful_valid_citations_not_flagged(self, mock_validate, mock_faithful):
        mock_validate.return_value = (True, False)
        mock_faithful.return_value = {"faithful": True, "unsupported_claims": []}

        result = hallucination_check_node(make_state(answer="COMP9900 is a capstone course."))

        assert result["hallucination_detected"] is False
        assert "fallback_reason" not in result

    @patch('rag.hallucination_checker.check_faithfulness')
    @patch('rag.hallucination_checker.validate_citations')
    def test_unfaithful_answer_flagged(self, mock_validate, mock_faithful):
        mock_validate.return_value = (True, False)
        mock_faithful.return_value = {"faithful": False, "unsupported_claims": ["invented prerequisite"]}

        result = hallucination_check_node(make_state(answer="COMP9900 requires COMP9999."))

        assert result["hallucination_detected"] is True
        assert "hallucination_detected" in result["processing_steps"]
        assert result["fallback_reason"] == "hallucination_retry"

    @patch('rag.hallucination_checker.check_faithfulness')
    @patch('rag.hallucination_checker.validate_citations')
    def test_invalid_citation_flagged_even_if_faithful(self, mock_validate, mock_faithful):
        """A fabricated citation must be caught even when the LLM judges content faithful"""
        mock_validate.return_value = (False, False)
        mock_faithful.return_value = {"faithful": True, "unsupported_claims": []}

        result = hallucination_check_node(make_state(answer="See [Fake](url)."))

        assert result["hallucination_detected"] is True

    @patch('rag.hallucination_checker.check_faithfulness')
    @patch('rag.hallucination_checker.validate_citations')
    def test_missing_citation_flagged(self, mock_validate, mock_faithful):
        mock_validate.return_value = (True, True)
        mock_faithful.return_value = {"faithful": True, "unsupported_claims": []}

        result = hallucination_check_node(make_state(answer="COMP9900 is a course, no sources."))

        assert result["hallucination_detected"] is True

    @patch('rag.hallucination_checker.check_faithfulness')
    @patch('rag.hallucination_checker.validate_citations')
    def test_empty_answer_flagged(self, mock_validate, mock_faithful):
        mock_validate.return_value = (True, False)
        mock_faithful.return_value = {"faithful": False, "unsupported_claims": ["(empty answer)"]}

        result = hallucination_check_node(make_state(answer=""))

        assert result["hallucination_detected"] is True


class TestFallbackNode:
    """fallback_node now sets fallback_used, not the overloaded fallback field (D3)"""

    @patch('ai.response_generator.generate_fallback_response')
    def test_sets_fallback_used_not_hallucination_detected(self, mock_fallback):
        mock_fallback.return_value = "I can help with UNSW CSE questions."

        result = fallback_node(make_state())

        assert result["fallback_used"] is True
        assert "hallucination_detected" not in result

    @patch('ai.response_generator.generate_fallback_response')
    def test_passes_fallback_reason_through(self, mock_fallback):
        """fallback_node must forward whichever reason triggered it (E2 in SPEC.md)"""
        mock_fallback.return_value = "answer"

        fallback_node(make_state(fallback_reason="no_relevant_docs"))

        mock_fallback.assert_called_once()
        _, kwargs = mock_fallback.call_args
        assert kwargs.get("reason") == "no_relevant_docs"


class TestRouteAfterHallucinationCheck:

    def test_detected_with_attempts_remaining_routes_to_fallback(self):
        state = make_state(hallucination_detected=True, generation_attempts=1)
        assert route_after_hallucination_check(state) == "fallback"

    def test_not_detected_routes_to_end(self):
        from langgraph.graph import END
        state = make_state(hallucination_detected=False, generation_attempts=1)
        assert route_after_hallucination_check(state) == END

    def test_detected_but_attempts_exhausted_routes_to_end(self):
        """
        Attempts exhausted means the answer is served as-is even though
        flagged -- this must not report fallback_used=True downstream
        (that field is now set only by fallback_node actually running,
        fixing the telemetry bug where the old shared `fallback` field
        would misreport this case).
        """
        from langgraph.graph import END
        state = make_state(hallucination_detected=True, generation_attempts=2)
        assert route_after_hallucination_check(state) == END
