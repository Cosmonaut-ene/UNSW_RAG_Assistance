"""
Unit tests for AI Safety Checker module
Tests content safety validation and filtering functionality
"""

import pytest
from unittest.mock import patch, MagicMock

from ai.safety_checker import is_query_safe_by_gemini
from test.mocks.mock_llm import create_mock_llm_with_responses


class TestSafetyChecker:
    """Test safety checking functionality"""
    
    @patch('ai.safety_checker.get_genai_model')
    def test_safe_unsw_query_passes(self, mock_get_genai):
        """Test that safe UNSW-related queries pass safety check"""
        mock_llm = create_mock_llm_with_responses("course_info")
        mock_llm.set_default_response("This query is about UNSW academic programs and is appropriate.")
        mock_get_genai.return_value = mock_llm
        
        safe_queries = [
            "What is COMP9900?",
            "Tell me about UNSW computer science programs",
            "Where is the CSE building located?",
            "What are the prerequisites for COMP2511?",
            "How do I apply to UNSW?"
        ]
        
        for query in safe_queries:
            result = is_query_safe_by_gemini(query)
            assert result is True, f"Query should be safe: {query}"
            
    @patch('ai.safety_checker.get_genai_model')
    def test_safety_checker_error_handling(self, mock_get_genai):
        """Test error handling when safety check fails"""
        mock_llm = MagicMock()
        mock_llm.generate_content.side_effect = Exception("API Error")
        mock_get_genai.return_value = mock_llm
        
        query = "What is COMP9900?"
        
        result = is_query_safe_by_gemini(query)
        
        # Should default to safe when check fails
        assert result is True
        
    @patch('ai.safety_checker.get_genai_model')
    def test_empty_response_handling(self, mock_get_genai):
        """Test handling of empty response from safety model"""
        mock_llm = MagicMock()
        mock_llm.generate_content.return_value.text = ""
        mock_get_genai.return_value = mock_llm
        
        query = "What is COMP9900?"
        
        result = is_query_safe_by_gemini(query)
        
        # Should default to safe when response is empty
        assert result is True
        
    @patch('ai.safety_checker.get_genai_model')
    def test_none_response_handling(self, mock_get_genai):
        """Test handling of None response from safety model"""
        mock_llm = MagicMock()
        mock_llm.generate_content.return_value.text = None
        mock_get_genai.return_value = mock_llm
        
        query = "What is COMP9900?"
        
        result = is_query_safe_by_gemini(query)
        
        # Should default to safe when response is None
        assert result is True


class TestSafetyCheckerEdgeCases:
    """Test edge cases and error scenarios"""
    
    @patch('ai.safety_checker.get_genai_model')
    def test_empty_query_handling(self, mock_get_genai):
        """Test handling of empty query input"""
        mock_llm = MagicMock()
        mock_get_genai.return_value = mock_llm
        
        result = is_query_safe_by_gemini("")
        
        # Empty query should be considered safe but LLM shouldn't be called
        assert result is True
        mock_llm.generate_content.assert_not_called()
        
    @patch('ai.safety_checker.get_genai_model')
    def test_none_query_handling(self, mock_get_genai):
        """Test handling of None query input"""
        mock_llm = MagicMock()
        mock_get_genai.return_value = mock_llm
        
        result = is_query_safe_by_gemini(None)
        
        # None query should be considered safe but LLM shouldn't be called
        assert result is True
        mock_llm.generate_content.assert_not_called()
        
    @patch('ai.safety_checker.get_genai_model')
    def test_special_characters_in_query(self, mock_get_genai):
        """Test handling of special characters in query"""
        mock_llm = MagicMock()
        mock_llm.generate_content.return_value.text = "This query contains special characters but is appropriate."
        mock_get_genai.return_value = mock_llm
        
        special_char_query = "What's the C++/Python requirement for COMP9900? (50% project) & other info"
        
        result = is_query_safe_by_gemini(special_char_query)
        
        # Should handle special characters without error
        assert result is True
        
    @patch('ai.safety_checker.get_genai_model')
    def test_unicode_characters_in_query(self, mock_get_genai):
        """Test handling of unicode characters in query"""
        mock_llm = MagicMock()
        mock_llm.generate_content.return_value.text = "This query with unicode characters is appropriate."
        mock_get_genai.return_value = mock_llm
        
        unicode_query = "UNSW的计算机科学课程如何？"  # Chinese: "How are UNSW's computer science programs?"
        
        result = is_query_safe_by_gemini(unicode_query)
        
        # Should handle unicode without error
        assert result is True


class TestSafetyCheckerResponseAnalysis:
    """Test safety checker response analysis logic"""
    
    @patch('ai.safety_checker.get_genai_model')
    def test_response_analysis_safe_indicators(self, mock_get_genai):
        """Test that responses with safe indicators return True"""
        mock_llm = MagicMock()
        
        safe_responses = [
            "This query is appropriate and relates to UNSW academic programs.",
            "The question is suitable for academic assistance at UNSW.",
            "This is a legitimate educational inquiry about computer science.",
            "The query asks about valid university programs and services.",
            "This question is appropriate for an educational chatbot."
        ]
        
        for response in safe_responses:
            mock_llm.generate_content.return_value.text = response
            result = is_query_safe_by_gemini("Test query")
            assert result is True, f"Response should indicate safe: {response}"
            
            
    @patch('ai.safety_checker.get_genai_model')
    def test_ambiguous_response_handling(self, mock_get_genai):
        """Test handling of ambiguous safety checker responses"""
        mock_llm = MagicMock()
        
        ambiguous_responses = [
            "This query might be appropriate depending on context.",
            "The question could be answered but needs clarification.",
            "This is a borderline case that requires judgment.",
            "The content is somewhat related to educational topics."
        ]
        
        for response in ambiguous_responses:
            mock_llm.generate_content.return_value.text = response
            result = is_query_safe_by_gemini("Test query")
            # Ambiguous responses should default to safe (benefit of doubt)
            assert result is True, f"Ambiguous response should default to safe: {response}"


class TestSafetyCheckerIntegration:
    """Integration tests for safety checker with realistic scenarios"""
    
    @patch('ai.safety_checker.get_genai_model')
    def test_course_inquiry_safety_check(self, mock_get_genai):
        """Test safety check for typical course inquiry"""
        mock_llm = MagicMock()
        mock_llm.generate_content.return_value.text = "This is a legitimate academic inquiry about UNSW courses."
        mock_get_genai.return_value = mock_llm
        
        query = "What are the prerequisites for COMP9900 and how challenging is the coursework?"
        
        result = is_query_safe_by_gemini(query)
        
        assert result is True
        
    @patch('ai.safety_checker.get_genai_model')
    def test_competitor_inquiry_safety_check(self, mock_get_genai):
        """Test safety check for competitor university inquiry"""
        mock_llm = MagicMock()
        mock_llm.generate_content.return_value.text = "This query asks about competing universities and should be redirected."
        mock_get_genai.return_value = mock_llm
        
        query = "How does UNSW computer science compare to University of Sydney's program?"
        
        result = is_query_safe_by_gemini(query)
        
        assert result is False
        
    @patch('ai.safety_checker.get_genai_model')
    def test_general_advice_safety_check(self, mock_get_genai):
        """Test safety check for general career advice"""
        mock_llm = MagicMock()
        mock_llm.generate_content.return_value.text = "This is appropriate career guidance suitable for students."
        mock_get_genai.return_value = mock_llm
        
        query = "What career paths are available for computer science graduates?"
        
        result = is_query_safe_by_gemini(query)
        
        assert result is True
        
    @patch('ai.safety_checker.get_genai_model')
    def test_location_inquiry_safety_check(self, mock_get_genai):
        """Test safety check for campus location inquiries"""
        mock_llm = MagicMock()
        mock_llm.generate_content.return_value.text = "This is a legitimate inquiry about campus facilities and locations."
        mock_get_genai.return_value = mock_llm
        
        query = "Where is the Computer Science building and what facilities are available there?"
        
        result = is_query_safe_by_gemini(query)
        
        assert result is True


class TestSafetyCheckerPerformance:
    """Test performance characteristics of safety checker"""
    
        
    @patch('ai.safety_checker.get_genai_model')
    def test_safety_check_with_model_reuse(self, mock_get_genai):
        """Test that safety checker reuses the same model instance"""
        mock_llm = MagicMock()
        mock_llm.generate_content.return_value.text = "This query is appropriate."
        mock_get_genai.return_value = mock_llm
        
        # Make multiple safety checks
        for i in range(3):
            is_query_safe_by_gemini(f"Test query {i}")
            
        # Should have called get_genai_model multiple times but gotten same instance
        assert mock_get_genai.call_count >= 3
        assert mock_llm.generate_content.call_count == 3