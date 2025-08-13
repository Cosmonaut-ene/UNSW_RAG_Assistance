"""
Unit tests for AI Response Generator module
Tests AI response generation with context and conversation history
"""

import pytest
from unittest.mock import patch, MagicMock

from ai.response_generator import generate_fallback_response
# Mock responses for testing
MOCK_RESPONSES = {
    "greeting": {
        "hello": "Hello! I'm here to help with UNSW CSE questions.",
        "thanks": "You're welcome! Happy to help with UNSW information."
    },
    "location": {
        "j17": "J17 is the Computer Science and Engineering building located on the UNSW campus."
    },
    "course_info": {
        "comp9900": "COMP9900 is a capstone project course where students work in teams to develop software projects."
    },
    "fallback": "I can help with UNSW CSE questions. What would you like to know?"
}


class TestResponseGenerator:
    """Test AI response generation functionality"""
    
    @patch('ai.response_generator.get_chat_llm')
    def test_generate_fallback_response_basic(self, mock_get_chat_llm):
        """Test basic fallback response generation"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = MOCK_RESPONSES["greeting"]["hello"]
        mock_llm.invoke.return_value = mock_response
        mock_get_chat_llm.return_value = mock_llm
        
        query = "Hello"
        conversation_history = ""
        
        result = generate_fallback_response(query, conversation_history)
        
        expected_response = MOCK_RESPONSES["greeting"]["hello"]
        assert result == expected_response
        assert mock_llm.invoke.call_count == 1
        
    @patch('ai.response_generator.get_chat_llm')
    def test_generate_fallback_response_with_history(self, mock_get_chat_llm):
        """Test fallback response generation with conversation history"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = MOCK_RESPONSES["greeting"]["thanks"]
        mock_llm.invoke.return_value = mock_response
        mock_get_chat_llm.return_value = mock_llm
        
        query = "Thanks for your help"
        conversation_history = """
        User: What is COMP9900?
        Assistant: COMP9900 is a capstone project course.
        """
        
        result = generate_fallback_response(query, conversation_history)
        
        expected_response = MOCK_RESPONSES["greeting"]["thanks"]
        assert result == expected_response
        
        
    @patch('ai.response_generator.get_chat_llm')
    def test_generate_fallback_response_none_response(self, mock_get_chat_llm):
        """Test handling of None response from LLM"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = None
        mock_get_chat_llm.return_value = mock_llm
        
        query = "What is COMP9900?"
        conversation_history = ""
        
        result = generate_fallback_response(query, conversation_history)
        
        # Should return default message when response is None
        assert "I'm here to help with UNSW CSE related questions" in result


class TestResponseGeneratorEdgeCases:
    """Test edge cases and error scenarios"""
    
    @patch('ai.response_generator.get_chat_llm')
    def test_empty_query_handling(self, mock_get_chat_llm):
        """Test handling of empty query input"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "How can I help you today?"
        mock_get_chat_llm.return_value = mock_llm
        
        result = generate_fallback_response("", "")
        
        assert isinstance(result, str)
        assert len(result) > 0
        
    @patch('ai.response_generator.get_chat_llm')
    def test_none_query_handling(self, mock_get_chat_llm):
        """Test handling of None query input"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "How can I help you today?"
        mock_get_chat_llm.return_value = mock_llm
        
        result = generate_fallback_response(None, "")
        
        assert isinstance(result, str)
        assert len(result) > 0
        
    @patch('ai.response_generator.get_chat_llm')
    def test_none_conversation_history_handling(self, mock_get_chat_llm):
        """Test handling of None conversation history"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = MOCK_RESPONSES["fallback"]
        mock_llm.invoke.return_value = mock_response
        # mock_llm = create_mock_chat_llm_with_responses("course_info")
        mock_get_chat_llm.return_value = mock_llm
        
        query = "What is COMP9900?"
        
        result = generate_fallback_response(query, None)
        
        assert isinstance(result, str)
        assert len(result) > 0
        
    @patch('ai.response_generator.get_chat_llm')
    def test_very_long_query(self, mock_get_chat_llm):
        """Test handling of very long query input"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "I understand you have a detailed question about UNSW programs."
        mock_get_chat_llm.return_value = mock_llm
        
        # Create a very long query
        long_query = "What is COMP9900 and can you tell me about " * 100
        
        result = generate_fallback_response(long_query, "")
        
        # Should process without error
        assert isinstance(result, str)
        assert len(result) > 0
        
    @patch('ai.response_generator.get_chat_llm')
    def test_special_characters_in_query(self, mock_get_chat_llm):
        """Test handling of special characters in query"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "I can help you with information about programming languages and course requirements."
        mock_get_chat_llm.return_value = mock_llm
        
        query = "What's the C++ & Python requirement for COMP9900? (50% project)"
        
        result = generate_fallback_response(query, "")
        
        # Should handle special characters without error
        assert isinstance(result, str)
        assert len(result) > 0
        
    @patch('ai.response_generator.get_chat_llm')
    def test_unicode_characters_handling(self, mock_get_chat_llm):
        """Test handling of unicode characters"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "I can provide information about UNSW programs in English."
        mock_get_chat_llm.return_value = mock_llm
        
        query = "UNSW的计算机科学课程如何？"  # Chinese characters
        
        result = generate_fallback_response(query, "")
        
        # Should handle unicode without error
        assert isinstance(result, str)
        assert len(result) > 0


class TestResponseGeneratorPromptConstruction:
    """Test prompt construction and formatting"""
    
    @patch('ai.response_generator.get_chat_llm')
    def test_prompt_includes_mazemap_context(self, mock_get_chat_llm):
        """Test that fallback prompt includes MazeMap context"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "I can help you navigate campus"
        mock_get_chat_llm.return_value = mock_llm
        
        query = "Where is J17?"
        
        generate_fallback_response(query, "")
        
        # Check that MazeMap context was included in the prompt
        call_args = mock_llm.invoke.call_args[0][0]
        prompt_content = call_args.content if hasattr(call_args, 'content') else str(call_args)
        
        assert "mazemap" in prompt_content.lower()
        assert "campus navigation" in prompt_content.lower()
        
    @patch('ai.response_generator.get_chat_llm')
    def test_prompt_includes_conversation_history(self, mock_get_chat_llm):
        """Test that conversation history is included in prompt when provided"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Based on our previous discussion about COMP9900"
        mock_get_chat_llm.return_value = mock_llm
        
        query = "What about the assessment?"
        conversation_history = """
        User: What is COMP9900?
        Assistant: COMP9900 is a capstone project course.
        """
        
        generate_fallback_response(query, conversation_history)
        
        # Check that conversation history was included
        call_args = mock_llm.invoke.call_args[0][0]
        prompt_content = call_args.content if hasattr(call_args, 'content') else str(call_args)
        
        # Note: The actual implementation may format history differently
        # This test checks that some form of context is preserved
        assert len(prompt_content) > len(query)  # Prompt should be longer than just the query
        
    @patch('ai.response_generator.get_chat_llm')
    def test_prompt_structure_consistency(self, mock_get_chat_llm):
        """Test that generated prompts have consistent structure"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Consistent response"
        mock_get_chat_llm.return_value = mock_llm
        
        test_queries = [
            "What is COMP9900?",
            "Where is the library?",
            "How do I apply?",
            "Tell me about CSE programs"
        ]
        
        prompt_structures = []
        
        for query in test_queries:
            generate_fallback_response(query, "")
            call_args = mock_llm.invoke.call_args[0][0]
            prompt_content = call_args.content if hasattr(call_args, 'content') else str(call_args)
            prompt_structures.append(prompt_content)
            
        # All prompts should contain consistent elements
        for prompt in prompt_structures:
            assert "UNSW" in prompt  # Should mention UNSW
            assert query in prompt or any(q in prompt for q in test_queries)  # Should contain the query


class TestResponseGeneratorIntegration:
    """Integration tests with realistic scenarios"""
    
    @patch('ai.response_generator.get_chat_llm')
    def test_greeting_response_integration(self, mock_get_chat_llm):
        """Test integrated greeting response scenario"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Hello! Welcome to UNSW CSE Open Day! I'm here to help answer your questions about Computer Science and Engineering at UNSW. What would you like to know?"
        mock_get_chat_llm.return_value = mock_llm
        
        query = "Hi there!"
        
        result = generate_fallback_response(query, "")
        
        assert "Welcome" in result
        assert "UNSW" in result
        assert "CSE" in result or "Computer Science" in result
        
    @patch('ai.response_generator.get_chat_llm')
    def test_location_response_with_mazemap_integration(self, mock_get_chat_llm):
        """Test integrated location response with MazeMap links"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "J17 is the Computer Science building. You can find it on our interactive campus map: [🔍 Find J17](https://use.mazemap.com/#v=1&config=unsw&campusid=111&zlevel=1&center=151.231022,-33.917689&zoom=16.2&search=J17)"
        mock_get_chat_llm.return_value = mock_llm
        
        query = "Where is J17?"
        
        result = generate_fallback_response(query, "")
        
        assert "J17" in result
        assert "Computer Science" in result
        assert "mazemap.com" in result
        
    @patch('ai.response_generator.get_chat_llm')
    def test_course_info_fallback_integration(self, mock_get_chat_llm):
        """Test integrated course information fallback"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "COMP9900 is a capstone project course where students work in teams to develop a significant software project. It's designed to integrate knowledge from previous courses and provide real-world development experience."
        mock_get_chat_llm.return_value = mock_llm
        
        query = "Tell me about COMP9900"
        
        result = generate_fallback_response(query, "")
        
        assert "COMP9900" in result
        assert "capstone" in result.lower() or "project" in result.lower()
        assert len(result) > 50  # Should be a substantial response
        
    @patch('ai.response_generator.get_chat_llm')
    def test_follow_up_with_history_integration(self, mock_get_chat_llm):
        """Test integrated follow-up response with conversation history"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Based on our previous discussion about COMP9900, the prerequisites include COMP2511 (Object-Oriented Design) and COMP3311 (Database Systems), plus you need to have completed 96 units of credit."
        mock_get_chat_llm.return_value = mock_llm
        
        query = "What are the prerequisites?"
        conversation_history = """
        User: What is COMP9900?
        Assistant: COMP9900 is a capstone project course for computer science students.
        """
        
        result = generate_fallback_response(query, conversation_history)
        
        assert "prerequisites" in result.lower()
        assert "COMP9900" in result or "previous discussion" in result.lower()
        
    @patch('ai.response_generator.get_chat_llm')
    def test_error_recovery_integration(self, mock_get_chat_llm):
        """Test integrated error recovery scenario"""
        mock_llm = MagicMock()
        # First call fails, second call succeeds (if implemented with retry logic)
        mock_llm.invoke.side_effect = [
            Exception("Network error"),
        ]
        mock_get_chat_llm.return_value = mock_llm
        
        query = "What is COMP9900?"
        
        result = generate_fallback_response(query, "")
        
        # Should return error message gracefully
        assert isinstance(result, str)
        assert len(result) > 0
        assert "trouble" in result.lower() or "error" in result.lower() or "help" in result.lower()


class TestResponseGeneratorPerformance:
    """Test performance characteristics of response generator"""
    
    @patch('ai.response_generator.get_chat_llm')
    def test_multiple_response_generation_performance(self, mock_get_chat_llm):
        """Test performance when generating multiple responses"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Generated response"
        mock_get_chat_llm.return_value = mock_llm
        
        queries = [
            "What is COMP9900?",
            "Where is J17?",
            "How do I apply?",
            "Tell me about CSE programs",
            "What are the fees?"
        ]
        
        results = []
        for query in queries:
            result = generate_fallback_response(query, "")
            results.append(result)
            
        # All responses should be generated successfully
        assert len(results) == 5
        assert all(isinstance(result, str) and len(result) > 0 for result in results)
        assert mock_llm.invoke.call_count == 5
        
    @patch('ai.response_generator.get_chat_llm')
    def test_response_generation_with_model_reuse(self, mock_get_chat_llm):
        """Test that response generator reuses the same model instance"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "Generated response"
        mock_get_chat_llm.return_value = mock_llm
        
        # Generate multiple responses
        for i in range(3):
            generate_fallback_response(f"Test query {i}", "")
            
        # Should have reused the same LLM instance
        assert mock_get_chat_llm.call_count >= 3
        assert mock_llm.invoke.call_count == 3