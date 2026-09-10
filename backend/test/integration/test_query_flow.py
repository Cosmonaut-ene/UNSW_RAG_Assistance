"""
Integration tests for complete query processing workflows
Tests end-to-end query processing from user input to response

Rewritten 2026-09-10: process_with_ai() used to call safety/rewrite/
retrieval/generation functions directly, and this file mocked each of
them individually. Since the LangGraph migration, process_with_ai()
only does a cache check + history retrieval and then delegates entirely
to rag.graph_rag.invoke_rag_graph() (see services/query_processor.py) --
the old mock targets (load_vector_store, HybridSearchEngine,
process_with_rag_detailed, ai.query_enhancer.get_chat_llm,
ai.safety_checker.get_genai_model, ai.response_generator.get_chat_llm)
no longer exist at the query_processor call boundary at all. Individual
graph nodes (safety_and_rewrite, generate, grade_documents,
hallucination_check) already have their own unit tests in
test/unit/test_rag/test_graph_rag.py -- this file's job is only to
verify process_with_ai()'s own thin layer: cache short-circuit, history
formatting, delegating to invoke_rag_graph(), and error handling. So it
mocks at that one real boundary instead of re-mocking graph internals.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.integration
class TestCompleteQueryFlow:
    """Test complete query processing workflow"""

    @patch('rag.graph_rag.invoke_rag_graph')
    @patch('services.query_processor.find_best_answer')
    def test_successful_rag_query_flow(self, mock_find_cache, mock_invoke_graph, mock_paths):
        """Test successful RAG query processing flow"""
        from services.query_processor import process_with_ai

        mock_find_cache.return_value = (None, False)  # No cache hit

        mock_invoke_graph.return_value = {
            "answer": "COMP9900 is a capstone project course for computer science students at UNSW.",
            "answered": True,
            "matched_files": ["handbook.pdf"],
            "retrieved_contexts": ["COMP9900 is a capstone project course"],
            "performance": {
                "response_time_ms": 500,
                "processing_steps": ["safety_check", "query_rewriting", "retrieval", "reranking", "crag_grading", "ai_generation"],
                "cache_hit": False,
                "fallback_used": False,
                "query_intent": "REWRITE",
                "fallback_reason": "",
                "safety_blocked": False,
            }
        }

        answer, answered, matched_files, performance = process_with_ai(
            "What is COMP9900?",
            session_id="test_session_123"
        )

        assert answered is True
        assert "COMP9900" in answer
        assert "capstone project" in answer
        assert "handbook.pdf" in matched_files
        # >= 0, not > 0: invoke_rag_graph is mocked to return instantly, so
        # the real wall-clock time process_with_ai measures around it can
        # legitimately round down to 0ms on a fast machine.
        assert performance["response_time_ms"] >= 0
        assert performance["cache_hit"] is False
        assert "ai_generation" in performance["processing_steps"]
        mock_invoke_graph.assert_called_once()

    @patch('services.query_processor.find_best_answer')
    def test_cached_query_flow(self, mock_find_cache):
        """Test query flow with cache hit"""
        from services.query_processor import process_with_ai

        # find_best_answer() returns (answer, found) -- a 2-tuple, not the
        # 3-tuple (answer, found, cache_entry) that the lower-level
        # find_cached_answer() it wraps returns.
        cached_answer = "COMP9900 is a capstone project course (from cache)"
        mock_find_cache.return_value = (cached_answer, True)

        answer, answered, matched_files, performance = process_with_ai(
            "What is COMP9900?",
            session_id="test_session_123"
        )

        assert answered is True
        assert answer == cached_answer
        assert performance["cache_hit"] is True
        assert "cache_hit" in performance["processing_steps"]
        assert performance["response_time_ms"] < 1000  # Should be fast

    @patch('rag.graph_rag.invoke_rag_graph')
    @patch('services.query_processor.find_best_answer')
    def test_safety_blocked_query_flow(self, mock_find_cache, mock_invoke_graph, mock_paths):
        """Test query flow when safety check blocks query"""
        from services.query_processor import process_with_ai

        mock_find_cache.return_value = (None, False)  # No cache hit

        # Real answer text and step name from rag/graph_rag.py's
        # safety_and_rewrite_node (safety_blocked branch).
        mock_invoke_graph.return_value = {
            "answer": "I can only help with UNSW-related questions. Please ask about UNSW programs and courses.",
            "answered": True,
            "matched_files": [],
            "retrieved_contexts": [],
            "performance": {
                "response_time_ms": 50,
                "processing_steps": ["safety_check", "safety_blocked"],
                "cache_hit": False,
                "fallback_used": False,
                "query_intent": "",
                "fallback_reason": "",
                "safety_blocked": True,
            }
        }

        answer, answered, matched_files, performance = process_with_ai(
            "Tell me about University of Sydney courses",
            session_id="test_session_123"
        )

        assert answered is True
        assert "UNSW-related questions" in answer
        assert performance["safety_blocked"] is True
        assert "safety_blocked" in performance["processing_steps"]

    @patch('rag.graph_rag.invoke_rag_graph')
    @patch('services.query_processor.find_best_answer')
    def test_fallback_query_flow(self, mock_find_cache, mock_invoke_graph, mock_paths):
        """Test query flow when RAG fails and fallback is used"""
        from services.query_processor import process_with_ai

        mock_find_cache.return_value = (None, False)  # No cache hit

        # Real step name is "fallback" (fallback_node); real
        # fallback_reason values are "navigation" | "no_relevant_docs" |
        # "hallucination_retry" (see RAGState in rag/graph_rag.py).
        mock_invoke_graph.return_value = {
            "answer": "I can help you with general information about UNSW programs.",
            "answered": True,
            "matched_files": [],
            "retrieved_contexts": [],
            "performance": {
                "response_time_ms": 300,
                "processing_steps": ["safety_check", "query_rewriting", "retrieval", "reranking", "crag_grading", "crag_incorrect", "fallback"],
                "cache_hit": False,
                "fallback_used": True,
                "query_intent": "REWRITE",
                "fallback_reason": "no_relevant_docs",
                "safety_blocked": False,
            }
        }

        answer, answered, matched_files, performance = process_with_ai(
            "What programs does UNSW offer?",
            session_id="test_session_123"
        )

        assert answered is True
        assert "UNSW programs" in answer
        assert performance["fallback_used"] is True
        assert "fallback" in performance["processing_steps"]
        assert performance["fallback_reason"] == "no_relevant_docs"

    @patch('services.query_processor.append_chat_log')
    @patch('services.query_processor.save_to_cache')
    def test_query_logging_and_caching(self, mock_save_cache, mock_append_log, mock_paths):
        """Test that queries are properly logged and cached"""
        from services.query_processor import save_to_admin_system

        mock_append_log.return_value = "test_message_id_123"

        message_id = save_to_admin_system(
            question="What is COMP9900?",
            answer="COMP9900 is a capstone project course.",
            answered=True,
            session_id="test_session_123",
            matched_files=["handbook.pdf"],
            performance_data={
                "response_time_ms": 500,
                "tokens_used": 100,
                "processing_steps": ["ai_generation"],
                "cache_hit": False
            }
        )

        assert message_id == "test_message_id_123"
        mock_append_log.assert_called_once()

        log_entry = mock_append_log.call_args[0][0]
        assert log_entry["question"] == "What is COMP9900?"
        assert log_entry["answer"] == "COMP9900 is a capstone project course."
        assert log_entry["answered"] is True
        assert log_entry["session_id"] == "test_session_123"
        assert log_entry["matched_files"] == ["handbook.pdf"]
        assert log_entry["response_time_ms"] == 500
        assert log_entry["tokens_used"] == 100

        mock_save_cache.assert_called_once()
        cache_call = mock_save_cache.call_args
        assert cache_call[1]["question"] == "What is COMP9900?"
        assert cache_call[1]["answer"] == "COMP9900 is a capstone project course."
        assert cache_call[1]["matched_files"] == ["handbook.pdf"]


@pytest.mark.integration
class TestConversationHistoryIntegration:
    """Test conversation history integration in query processing"""

    @patch('rag.graph_rag.invoke_rag_graph')
    @patch('services.query_processor.load_all_chat_logs')
    @patch('services.query_processor.find_best_answer')
    def test_conversation_history_retrieval_and_usage(self, mock_find_cache, mock_load_logs, mock_invoke_graph):
        """Test that conversation history is retrieved and passed to the graph"""
        from services.query_processor import process_with_ai

        mock_load_logs.return_value = [
            {
                "session_id": "test_session_123",
                "question": "What is COMP9900?",
                "answer": "COMP9900 is a capstone project course.",
                "answered": True,
                "timestamp": "2025-01-01T10:00:00+11:00"
            },
            {
                "session_id": "test_session_123",
                "question": "What are the prerequisites?",
                "answer": "Prerequisites include COMP2511 and COMP3311.",
                "answered": True,
                "timestamp": "2025-01-01T10:01:00+11:00"
            },
            {
                "session_id": "other_session",
                "question": "Different session question",
                "answer": "Different session answer",
                "answered": True,
                "timestamp": "2025-01-01T09:00:00+11:00"
            }
        ]

        mock_find_cache.return_value = (None, False)  # No cache hit

        mock_invoke_graph.return_value = {
            "answer": "Based on our previous discussion about COMP9900, the assessment includes project work and presentations.",
            "answered": True,
            "matched_files": [],
            "retrieved_contexts": [],
            "performance": {
                "response_time_ms": 400,
                "processing_steps": ["fallback"],
                "cache_hit": False,
                "fallback_used": True,
                "query_intent": "REWRITE",
                "fallback_reason": "no_relevant_docs",
                "safety_blocked": False,
            }
        }

        process_with_ai(
            "What about the assessment?",
            session_id="test_session_123"
        )

        # process_with_ai formats history and passes it through to the
        # graph as formatted_history -- verify only the current session's
        # two prior turns made it in, not the other session's turn.
        mock_invoke_graph.assert_called_once()
        call_kwargs = mock_invoke_graph.call_args.kwargs
        formatted_history = call_kwargs.get("formatted_history", "")
        assert "COMP9900" in formatted_history
        assert "capstone project" in formatted_history
        assert "Different session" not in formatted_history


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Test error handling in integrated workflows"""

    @patch('rag.graph_rag.invoke_rag_graph')
    @patch('services.query_processor.find_best_answer')
    def test_multiple_component_failures(self, mock_find_cache, mock_invoke_graph, mock_paths):
        """Test graceful handling when the graph itself raises"""
        from services.query_processor import process_with_ai

        mock_find_cache.return_value = (None, False)  # No cache hit
        mock_invoke_graph.side_effect = Exception("Safety API unavailable")

        answer, answered, matched_files, performance = process_with_ai(
            "What is COMP9900?",
            session_id="test_session_123"
        )

        # process_with_ai's except-branch returns a fixed message and
        # answered=False -- see services/query_processor.py
        assert isinstance(answer, str)
        assert len(answer) > 0
        assert answered is False
        assert "graph_error" in performance["processing_steps"]

    @patch('rag.graph_rag.invoke_rag_graph')
    @patch('services.query_processor.find_best_answer')
    def test_network_timeout_handling(self, mock_find_cache, mock_invoke_graph, mock_paths):
        """Test handling of network timeouts"""
        from services.query_processor import process_with_ai

        mock_find_cache.return_value = (None, False)  # No cache hit
        mock_invoke_graph.side_effect = TimeoutError("Request timeout")

        answer, answered, matched_files, performance = process_with_ai(
            "What is COMP9900?",
            session_id="test_session_123"
        )

        assert isinstance(answer, str)
        assert answered is False
        assert "no_answer" in performance["processing_steps"]


@pytest.mark.integration
@pytest.mark.performance
class TestQueryFlowPerformance:
    """Test performance characteristics of integrated query flow"""

    @patch('rag.graph_rag.invoke_rag_graph')
    @patch('services.query_processor.find_best_answer')
    def test_query_processing_performance(self, mock_find_cache, mock_invoke_graph, mock_paths):
        """Test that query processing completes within reasonable time"""
        from services.query_processor import process_with_ai

        mock_find_cache.return_value = (None, False)  # No cache hit

        mock_invoke_graph.return_value = {
            "answer": "Quick response",
            "answered": True,
            "matched_files": [],
            "retrieved_contexts": [],
            "performance": {
                "response_time_ms": 200,
                "processing_steps": ["fallback"],
                "cache_hit": False,
                "fallback_used": True,
                "query_intent": "",
                "fallback_reason": "no_relevant_docs",
                "safety_blocked": False,
            }
        }

        answer, answered, matched_files, performance = process_with_ai(
            "What is COMP9900?",
            session_id="test_session_123"
        )

        # >= 0, not > 0: invoke_rag_graph is mocked to return instantly, so
        # the real wall-clock time process_with_ai measures around it can
        # legitimately round down to 0ms on a fast machine.
        assert performance["response_time_ms"] >= 0
        assert performance["response_time_ms"] < 5000  # Should complete within 5 seconds
        assert performance["tokens_used"] > 0
        assert len(performance["processing_steps"]) > 0

    @patch('services.query_processor.find_best_answer')
    def test_cache_hit_performance(self, mock_find_cache):
        """Test that cache hits are significantly faster"""
        from services.query_processor import process_with_ai

        cached_answer = "Fast cached response"
        mock_find_cache.return_value = (cached_answer, True)

        answer, answered, matched_files, performance = process_with_ai(
            "Cached query",
            session_id="test_session_123"
        )

        assert performance["response_time_ms"] < 100  # Should be under 100ms
        assert performance["cache_hit"] is True
        assert answer == cached_answer
