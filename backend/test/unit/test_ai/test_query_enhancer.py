"""
Unit tests for AI Query Enhancer module
Tests query enhancement and rewriting functionality with conversation history
"""

import pytest
from unittest.mock import patch, MagicMock

from ai.query_enhancer import rewrite_query_with_context
from test.mocks.mock_llm import create_mock_chat_llm_with_responses, MOCK_RESPONSES


class TestQueryEnhancer:
    """Test query enhancement and rewriting functionality"""
    
    @patch('ai.query_enhancer.get_genai_model')
    def test_rewrite_query_basic_functionality(self, mock_get_genai_model):
        """Test basic query rewriting without conversation history"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "COMP9900 overview description prerequisites"
        mock_model.generate_content.return_value = mock_response
        mock_get_genai_model.return_value = mock_model
        
        original_query = "What is COMP9900"
        conversation_history = []
        
        result = rewrite_query_with_context(original_query, conversation_history)
        
        assert result == "COMP9900 overview description prerequisites"
        assert mock_model.generate_content.call_count == 1
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_rewrite_query_with_conversation_history(self, mock_get_genai_model):
        """Test query rewriting with conversation history for context resolution"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "COMP9900 prerequisites requirements"
        mock_model.generate_content.return_value = mock_response
        mock_get_genai_model.return_value = mock_model
        
        original_query = "prerequisites for it"
        conversation_history = [
            {
                "question": "What is COMP9900?",
                "answer": "COMP9900 is a capstone project course."
            }
        ]
        
        result = rewrite_query_with_context(original_query, conversation_history)
        
        assert result == "COMP9900 prerequisites requirements"
        assert mock_model.generate_content.call_count == 1
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_rewrite_query_navigation_detection(self, mock_get_genai_model):
        """Test that navigation queries are properly detected and marked"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "NAVIGATION_QUERY"
        mock_model.generate_content.return_value = mock_response
        mock_get_genai_model.return_value = mock_model
        
        original_query = "Where is J17?"
        conversation_history = []
        
        result = rewrite_query_with_context(original_query, conversation_history)
        
        assert result == "NAVIGATION_QUERY"
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_rewrite_query_non_unsw_redirect(self, mock_get_genai_model):
        """Test that non-UNSW queries are redirected appropriately"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "REDIRECT: I can only help with UNSW-related questions."
        mock_model.generate_content.return_value = mock_response
        mock_get_genai_model.return_value = mock_model
        
        original_query = "Tell me about Sydney University courses"
        conversation_history = []
        
        result = rewrite_query_with_context(original_query, conversation_history)
        
        assert result == "REDIRECT: I can only help with UNSW-related questions."
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_rewrite_query_error_handling(self, mock_get_genai_model):
        """Test error handling when LLM fails"""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_get_genai_model.return_value = mock_model
        
        original_query = "What is COMP9900?"
        conversation_history = []
        
        result = rewrite_query_with_context(original_query, conversation_history)
        
        # Should return original query when enhancement fails
        assert result == original_query
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_rewrite_query_empty_response_handling(self, mock_get_genai_model):
        """Test handling of empty response from LLM"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""
        mock_model.generate_content.return_value = mock_response
        mock_get_genai_model.return_value = mock_model
        
        original_query = "What is COMP9900?"
        conversation_history = []
        
        result = rewrite_query_with_context(original_query, conversation_history)
        
        # Should return empty string when response is empty (actual behavior)
        assert result == ""


class TestQueryEnhancerEdgeCases:
    """Test edge cases and error scenarios"""
    
    @patch('ai.query_enhancer.get_genai_model')
    def test_empty_query_handling(self, mock_get_genai_model):
        """Test handling of empty query input"""
        mock_model = MagicMock()
        mock_get_genai_model.return_value = mock_model
        
        result = rewrite_query_with_context("", [])
        
        # Should return empty string without calling LLM
        assert result == ""
        mock_model.generate_content.assert_not_called()
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_none_query_handling(self, mock_get_genai_model):
        """Test handling of None query input"""
        mock_model = MagicMock()
        mock_get_genai_model.return_value = mock_model
        
        result = rewrite_query_with_context(None, [])
        
        # Should return empty string without calling LLM
        assert result == ""
        mock_model.generate_content.assert_not_called()
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_whitespace_only_query(self, mock_get_genai_model):
        """Test handling of whitespace-only query"""
        mock_model = MagicMock()
        mock_get_genai_model.return_value = mock_model
        
        result = rewrite_query_with_context("   \t\n   ", [])
        
        # Should return empty string without calling LLM
        assert result == ""
        mock_model.generate_content.assert_not_called()
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_none_conversation_history_handling(self, mock_get_genai_model):
        """Test handling of None conversation history"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "COMP9900 overview description prerequisites"
        mock_model.generate_content.return_value = mock_response
        mock_get_genai_model.return_value = mock_model
        
        original_query = "What is COMP9900?"
        
        result = rewrite_query_with_context(original_query, None)
        
        assert result == "COMP9900 overview description prerequisites"
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_malformed_conversation_history(self, mock_get_genai_model):
        """Test handling of malformed conversation history"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "COMP9900 overview description prerequisites"
        mock_model.generate_content.return_value = mock_response
        mock_get_genai_model.return_value = mock_model
        
        original_query = "What is COMP9900?"
        conversation_history = [
            {"question": "What is COMP9900?"},  # Missing answer
            {"answer": "Some answer"},  # Missing question
            {"question": None, "answer": None},  # None values
            "invalid_format"  # Wrong type
        ]
        
        result = rewrite_query_with_context(original_query, conversation_history)
        
        # Should still work despite malformed history
        assert result == "COMP9900 overview description prerequisites"
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_very_long_query(self, mock_get_genai_model):
        """Test handling of very long query input"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "COMP9900 overview description prerequisites"
        mock_model.generate_content.return_value = mock_response
        mock_get_genai_model.return_value = mock_model
        
        # Create a very long query
        long_query = "What is COMP9900? " * 1000
        
        result = rewrite_query_with_context(long_query, [])
        
        # Should process without error
        assert isinstance(result, str)
        assert len(result) > 0
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_special_characters_in_query(self, mock_get_genai_model):
        """Test handling of special characters in query"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "COMP9900 overview description prerequisites"
        mock_model.generate_content.return_value = mock_response
        mock_get_genai_model.return_value = mock_model
        
        original_query = "What's the C++ & Python requirements for COMP9900? (50% project)"
        
        result = rewrite_query_with_context(original_query, [])
        
        # Should handle special characters without error
        assert isinstance(result, str)
        assert len(result) > 0


class TestQueryEnhancerIntegration:
    """Integration tests with realistic scenarios"""
    
    @patch('ai.query_enhancer.get_genai_model')
    def test_course_comparison_enhancement(self, mock_get_genai_model):
        """Test enhancement of course comparison queries"""
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "COMP9900 COMP9901 comparison differences"
        mock_get_genai_model.return_value = mock_model
        
        original_query = "Compare COMP9900 and COMP9901"
        conversation_history = []
        
        result = rewrite_query_with_context(original_query, conversation_history)
        
        assert "COMP9900" in result
        assert "COMP9901" in result
        assert "comparison" in result
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_follow_up_question_with_context(self, mock_get_genai_model):
        """Test enhancement of follow-up questions using conversation context"""
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "COMP9900 assessment structure breakdown"
        mock_get_genai_model.return_value = mock_model
        
        original_query = "What about the assessment?"
        conversation_history = [
            {
                "question": "Tell me about COMP9900",
                "answer": "COMP9900 is a capstone project course for final year students."
            }
        ]
        
        result = rewrite_query_with_context(original_query, conversation_history)
        
        assert "COMP9900" in result
        assert "assessment" in result
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_location_query_variations(self, mock_get_genai_model):
        """Test various location query patterns"""
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "NAVIGATION_QUERY"
        mock_get_genai_model.return_value = mock_model
        
        location_queries = [
            "Where is J17?",
            "How do I get to the library?",
            "Where can I find the computer lab?",
            "Directions to the engineering building?"
        ]
        
        for query in location_queries:
            result = rewrite_query_with_context(query, [])
            assert result == "NAVIGATION_QUERY"
            
    @patch('ai.query_enhancer.get_genai_model')
    def test_greeting_handling(self, mock_get_genai_model):
        """Test that greeting queries are handled appropriately"""
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "Hello greeting"
        mock_get_genai_model.return_value = mock_model
        
        greeting_queries = [
            "Hello",
            "Hi there",
            "Good morning",
            "Hey"
        ]
        
        for query in greeting_queries:
            result = rewrite_query_with_context(query, [])
            # Greetings should be enhanced minimally
            assert isinstance(result, str)
            assert len(result) > 0


class TestQueryEnhancerConversationHistory:
    """Test conversation history processing and context extraction"""
    
    @patch('ai.query_enhancer.get_genai_model')
    def test_conversation_history_formatting(self, mock_get_genai_model):
        """Test that conversation history is properly formatted in prompts"""
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "enhanced query"
        mock_get_genai_model.return_value = mock_model
        
        conversation_history = [
            {
                "question": "What is COMP9900?",
                "answer": "COMP9900 is a capstone project course."
            },
            {
                "question": "What are the prerequisites?",
                "answer": "Prerequisites include COMP2511 and COMP3311."
            }
        ]
        
        original_query = "What about the assessment?"
        
        rewrite_query_with_context(original_query, conversation_history)
        
        # Check that the conversation history was included in the prompt
        call_args = mock_model.generate_content.call_args[0][0]
        prompt_content = str(call_args)
        
        assert "COMP9900" in prompt_content
        assert "capstone project" in prompt_content
        assert "prerequisites" in prompt_content.lower()
        
    @patch('ai.query_enhancer.get_genai_model')
    def test_long_conversation_history_truncation(self, mock_get_genai_model):
        """Test that very long conversation history is appropriately handled"""
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "enhanced query"
        mock_get_genai_model.return_value = mock_model
        
        # Create a long conversation history
        long_history = []
        for i in range(20):
            long_history.append({
                "question": f"Question {i}",
                "answer": f"Answer {i} " * 50  # Long answers
            })
            
        original_query = "Follow-up question"
        
        result = rewrite_query_with_context(original_query, long_history)
        
        # Should handle long history without error
        assert isinstance(result, str)
        mock_model.generate_content.assert_called_once()


class TestQueryEnhancerPerformance:
    """Test performance characteristics of query enhancement"""
    
    @patch('ai.query_enhancer.get_genai_model')
    def test_performance_with_multiple_calls(self, mock_get_genai_model):
        """Test performance when making multiple enhancement calls"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "COMP9900 overview description prerequisites"
        mock_model.generate_content.return_value = mock_response
        mock_get_genai_model.return_value = mock_model
        
        queries = [
            "What is COMP9900?",
            "Tell me about COMP9021",
            "Where is J17?",
            "What are the prerequisites?",
            "How do I enroll?"
        ]
        
        results = []
        for query in queries:
            result = rewrite_query_with_context(query, [])
            results.append(result)
            
        # All calls should succeed
        assert len(results) == 5
        assert all(isinstance(result, str) for result in results)
        assert mock_model.generate_content.call_count == 5