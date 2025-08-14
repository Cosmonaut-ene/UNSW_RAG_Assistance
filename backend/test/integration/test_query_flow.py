"""
Integration tests for complete query processing workflows
Tests end-to-end query processing from user input to response
"""

import pytest
from unittest.mock import patch, MagicMock
import json

from services.query_processor import process_with_ai, save_to_admin_system
from test.mocks.mock_llm import create_mock_chat_llm_with_responses
from test.mocks.mock_vector_store import MockVectorStore


@pytest.mark.integration
class TestCompleteQueryFlow:
    """Test complete query processing workflow"""
    
    @patch('services.query_processor.process_with_rag_detailed')
    @patch('services.query_processor.find_best_answer')
    @patch('ai.query_enhancer.get_chat_llm')
    @patch('ai.safety_checker.get_genai_model')
    @patch('services.query_processor.HybridSearchEngine')
    @patch('services.query_processor.load_vector_store')
    def test_successful_rag_query_flow(self, mock_load_vector_store, mock_hybrid_class,
                                     mock_safety_llm, mock_enhancer_llm, mock_find_cache,
                                     mock_rag_process, mock_paths):
        """Test successful RAG query processing flow"""
        
        # Setup mocks
        mock_find_cache.return_value = (None, False, None)  # No cache hit
        
        mock_safety_model = MagicMock()
        mock_safety_model.generate_content.return_value.text = "This query is appropriate for UNSW assistance"
        mock_safety_llm.return_value = mock_safety_model
        
        mock_enhancer = create_mock_chat_llm_with_responses("query_enhancement")
        mock_enhancer_llm.return_value = mock_enhancer
        
        mock_vector_store = MockVectorStore()
        mock_load_vector_store.return_value = mock_vector_store
        
        mock_rag_process.return_value = {
            "search_results": [
                {
                    "page_content": "COMP9900 is a capstone project course",
                    "metadata": {"source": "handbook.pdf", "course_code": "COMP9900"}
                }
            ]
        }
        
        mock_hybrid_engine = MagicMock()
        mock_hybrid_results = [
            {
                "page_content": "COMP9900 is a capstone project course for computer science students",
                "metadata": {
                    "source": "handbook.pdf",
                    "course_code": "COMP9900",
                    "hybrid_score": 85.0
                }
            }
        ]
        mock_hybrid_engine.search_hybrid.return_value = mock_hybrid_results
        mock_hybrid_class.return_value = mock_hybrid_engine
        
        with patch('services.query_processor.ai_process_query') as mock_ai_process:
            mock_ai_process.return_value = {
                "answer": "COMP9900 is a capstone project course for computer science students at UNSW.",
                "safety_blocked": False,
                "matched_files": ["handbook.pdf"]
            }
            
            # Execute query
            answer, answered, matched_files, performance = process_with_ai(
                "What is COMP9900?", 
                session_id="test_session_123"
            )
            
            # Verify results
            assert answered is True
            assert "COMP9900" in answer
            assert "capstone project" in answer
            assert "handbook.pdf" in matched_files
            assert performance["response_time_ms"] > 0
            assert performance["cache_hit"] is False
            assert "rag_success" in performance["processing_steps"]
            
    @patch('services.query_processor.find_best_answer')
    @patch('ai.safety_checker.get_genai_model')
    def test_cached_query_flow(self, mock_safety_llm, mock_find_cache):
        """Test query flow with cache hit"""
        
        # Setup cache hit
        cached_answer = "COMP9900 is a capstone project course (from cache)"
        mock_find_cache.return_value = (cached_answer, True, {"cache_id": "test_cache"})
        
        # Execute query
        answer, answered, matched_files, performance = process_with_ai(
            "What is COMP9900?",
            session_id="test_session_123"
        )
        
        # Verify cache hit
        assert answered is True
        assert answer == cached_answer
        assert performance["cache_hit"] is True
        assert "cache_hit" in performance["processing_steps"]
        assert performance["response_time_ms"] < 1000  # Should be fast
        
    @patch('services.query_processor.find_best_answer')
    @patch('ai.safety_checker.get_genai_model')
    def test_safety_blocked_query_flow(self, mock_safety_llm, mock_find_cache):
        """Test query flow when safety check blocks query"""
        
        mock_find_cache.return_value = (None, False, None)  # No cache hit
        
        # Setup safety check to block
        mock_safety_model = MagicMock()
        mock_safety_model.generate_content.return_value.text = "This query is inappropriate and should be blocked"
        mock_safety_llm.return_value = mock_safety_model
        
        # Execute query
        answer, answered, matched_files, performance = process_with_ai(
            "Tell me about University of Sydney courses",
            session_id="test_session_123"
        )
        
        # Verify safety blocking
        assert answered is True
        assert "UNSW-related questions" in answer
        assert performance["safety_blocked"] is True
        assert "safety_warning_returned" in performance["processing_steps"]
        
    @patch('services.query_processor.process_with_rag_detailed')
    @patch('services.query_processor.find_best_answer')
    @patch('ai.query_enhancer.get_chat_llm')
    @patch('ai.safety_checker.get_genai_model')
    @patch('services.query_processor.HybridSearchEngine')
    @patch('services.query_processor.load_vector_store')
    @patch('ai.response_generator.get_chat_llm')
    def test_fallback_query_flow(self, mock_fallback_llm, mock_load_vector_store, 
                                mock_hybrid_class, mock_safety_llm, mock_enhancer_llm,
                                mock_find_cache, mock_rag_process):
        """Test query flow when RAG fails and fallback is used"""
        
        # Setup mocks for failed RAG
        mock_find_cache.return_value = (None, False, None)  # No cache hit
        
        mock_safety_model = MagicMock()
        mock_safety_model.generate_content.return_value.text = "This query is appropriate"
        mock_safety_llm.return_value = mock_safety_model
        
        mock_enhancer = create_mock_chat_llm_with_responses("query_enhancement")
        mock_enhancer_llm.return_value = mock_enhancer
        
        mock_vector_store = MockVectorStore()
        mock_load_vector_store.return_value = mock_vector_store
        
        # RAG returns no results
        mock_rag_process.return_value = {"search_results": []}
        
        mock_hybrid_engine = MagicMock()
        mock_hybrid_engine.search_hybrid.return_value = []  # No hybrid results
        mock_hybrid_class.return_value = mock_hybrid_engine
        
        # Setup fallback LLM
        mock_fallback = MagicMock()
        mock_fallback.invoke.return_value.content = "I can help you with general information about UNSW programs."
        mock_fallback_llm.return_value = mock_fallback
        
        # Execute query
        answer, answered, matched_files, performance = process_with_ai(
            "What programs does UNSW offer?",
            session_id="test_session_123"
        )
        
        # Verify fallback was used
        assert answered is True
        assert "UNSW programs" in answer
        assert performance["fallback_used"] is True
        assert "no_search_results_fallback" in performance["processing_steps"]
        
    @patch('services.query_processor.append_chat_log')
    @patch('services.query_processor.save_to_cache')
    def test_query_logging_and_caching(self, mock_save_cache, mock_append_log, mock_paths):
        """Test that queries are properly logged and cached"""
        
        mock_append_log.return_value = "test_message_id_123"
        
        # Test saving successful query
        message_id = save_to_admin_system(
            question="What is COMP9900?",
            answer="COMP9900 is a capstone project course.",
            answered=True,
            session_id="test_session_123",
            matched_files=["handbook.pdf"],
            performance_data={
                "response_time_ms": 500,
                "tokens_used": 100,
                "processing_steps": ["rag_success"],
                "cache_hit": False
            }
        )
        
        # Verify logging
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
        
        # Verify caching
        mock_save_cache.assert_called_once()
        cache_call = mock_save_cache.call_args
        assert cache_call[1]["question"] == "What is COMP9900?"
        assert cache_call[1]["answer"] == "COMP9900 is a capstone project course."
        assert cache_call[1]["matched_files"] == ["handbook.pdf"]


@pytest.mark.integration
class TestConversationHistoryIntegration:
    """Test conversation history integration in query processing"""
    
    @patch('services.query_processor.load_all_chat_logs')
    @patch('services.query_processor.find_best_answer')
    @patch('ai.query_enhancer.get_chat_llm')
    @patch('ai.safety_checker.get_genai_model')
    def test_conversation_history_retrieval_and_usage(self, mock_safety_llm, mock_enhancer_llm,
                                                     mock_find_cache, mock_load_logs):
        """Test that conversation history is properly retrieved and used"""
        
        # Setup conversation history
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
        
        mock_find_cache.return_value = (None, False, None)  # No cache hit
        
        mock_safety_model = MagicMock()
        mock_safety_model.generate_content.return_value.text = "This query is appropriate"
        mock_safety_llm.return_value = mock_safety_model
        
        # Setup query enhancer to use history
        mock_enhancer = MagicMock()
        mock_enhancer.invoke.return_value.content = "COMP9900 assessment structure breakdown"
        mock_enhancer_llm.return_value = mock_enhancer
        
        with patch('services.query_processor.process_with_rag_detailed') as mock_rag:
            mock_rag.return_value = {"search_results": []}
            
            with patch('services.query_processor.HybridSearchEngine'):
                with patch('ai.response_generator.get_chat_llm') as mock_fallback:
                    mock_fallback_llm = MagicMock()
                    mock_fallback_llm.invoke.return_value.content = "Based on our previous discussion about COMP9900, the assessment includes project work and presentations."
                    mock_fallback.return_value = mock_fallback_llm
                    
                    # Execute query with follow-up question
                    answer, answered, matched_files, performance = process_with_ai(
                        "What about the assessment?",
                        session_id="test_session_123"
                    )
                    
                    # Verify that query enhancement was called with history context
                    mock_enhancer.invoke.assert_called_once()
                    enhancer_call = mock_enhancer.invoke.call_args[0][0]
                    
                    # The prompt should include conversation history
                    prompt_content = enhancer_call.content if hasattr(enhancer_call, 'content') else str(enhancer_call)
                    assert "COMP9900" in prompt_content
                    assert "capstone project" in prompt_content


@pytest.mark.integration  
class TestErrorHandlingIntegration:
    """Test error handling in integrated workflows"""
    
    @patch('services.query_processor.find_best_answer')
    @patch('ai.safety_checker.get_genai_model')
    def test_multiple_component_failures(self, mock_safety_llm, mock_find_cache):
        """Test graceful handling when multiple components fail"""
        
        mock_find_cache.return_value = (None, False, None)  # No cache hit
        
        # Safety check fails
        mock_safety_llm.side_effect = Exception("Safety API unavailable")
        
        with patch('ai.query_enhancer.get_chat_llm') as mock_enhancer_llm:
            # Query enhancer also fails
            mock_enhancer_llm.side_effect = Exception("Query enhancer API unavailable")
            
            # Execute query
            answer, answered, matched_files, performance = process_with_ai(
                "What is COMP9900?",
                session_id="test_session_123"
            )
            
            # Should still return some response (fallback)
            assert isinstance(answer, str)
            assert len(answer) > 0
            # May or may not be answered depending on fallback behavior
            
    @patch('services.query_processor.find_best_answer')
    @patch('ai.safety_checker.get_genai_model') 
    def test_network_timeout_handling(self, mock_safety_llm, mock_find_cache):
        """Test handling of network timeouts"""
        
        mock_find_cache.return_value = (None, False, None)  # No cache hit
        
        mock_safety_model = MagicMock()
        mock_safety_model.generate_content.return_value.text = "This query is appropriate"
        mock_safety_llm.return_value = mock_safety_model
        
        with patch('ai.query_enhancer.get_chat_llm') as mock_enhancer_llm:
            mock_enhancer = MagicMock()
            # Simulate timeout
            mock_enhancer.invoke.side_effect = TimeoutError("Request timeout")
            mock_enhancer_llm.return_value = mock_enhancer
            
            # Execute query
            answer, answered, matched_files, performance = process_with_ai(
                "What is COMP9900?",
                session_id="test_session_123"
            )
            
            # Should handle timeout gracefully
            assert isinstance(answer, str)
            # Should indicate that original query was returned due to enhancement failure
            

@pytest.mark.integration
@pytest.mark.performance
class TestQueryFlowPerformance:
    """Test performance characteristics of integrated query flow"""
    
    @patch('services.query_processor.find_best_answer')
    @patch('ai.safety_checker.get_genai_model')
    @patch('ai.query_enhancer.get_chat_llm')
    def test_query_processing_performance(self, mock_enhancer_llm, mock_safety_llm, mock_find_cache):
        """Test that query processing completes within reasonable time"""
        
        # Setup fast mocks
        mock_find_cache.return_value = (None, False, None)  # No cache hit
        
        mock_safety_model = MagicMock()
        mock_safety_model.generate_content.return_value.text = "Query is appropriate"
        mock_safety_llm.return_value = mock_safety_model
        
        mock_enhancer = MagicMock()
        mock_enhancer.invoke.return_value.content = "enhanced query"
        mock_enhancer_llm.return_value = mock_enhancer
        
        with patch('services.query_processor.process_with_rag_detailed') as mock_rag:
            mock_rag.return_value = {"search_results": []}
            
            with patch('services.query_processor.HybridSearchEngine'):
                with patch('ai.response_generator.get_chat_llm') as mock_fallback:
                    mock_fallback_llm = MagicMock()
                    mock_fallback_llm.invoke.return_value.content = "Quick response"
                    mock_fallback.return_value = mock_fallback_llm
                    
                    # Execute query and measure time
                    answer, answered, matched_files, performance = process_with_ai(
                        "What is COMP9900?",
                        session_id="test_session_123"
                    )
                    
                    # Verify performance metrics
                    assert performance["response_time_ms"] > 0
                    assert performance["response_time_ms"] < 5000  # Should complete within 5 seconds
                    assert performance["tokens_used"] > 0
                    assert len(performance["processing_steps"]) > 0
                    
    @patch('services.query_processor.find_best_answer')
    def test_cache_hit_performance(self, mock_find_cache):
        """Test that cache hits are significantly faster"""
        
        # Setup cache hit
        cached_answer = "Fast cached response"
        mock_find_cache.return_value = (cached_answer, True, {"cache_id": "test"})
        
        # Execute query
        answer, answered, matched_files, performance = process_with_ai(
            "Cached query",
            session_id="test_session_123"
        )
        
        # Cache hits should be very fast
        assert performance["response_time_ms"] < 100  # Should be under 100ms
        assert performance["cache_hit"] is True
        assert answer == cached_answer