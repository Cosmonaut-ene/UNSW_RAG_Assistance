"""
Unit tests for AI Prompt Manager module
Tests prompt templates and engineering functionality
"""

import pytest
from langchain.prompts import PromptTemplate

from ai.prompt_manager import PromptManager


class TestPromptManager:
    """Test prompt template management and rendering"""
    
    def test_get_rag_prompt_template_structure(self):
        """Test that RAG prompt template has correct structure"""
        template = PromptManager.get_rag_prompt_template()
        
        assert isinstance(template, PromptTemplate)
        assert "context" in template.input_variables
        assert "question" in template.input_variables
        assert len(template.input_variables) == 2
        
    def test_get_rag_prompt_template_content(self):
        """Test that RAG prompt template contains expected content"""
        template = PromptManager.get_rag_prompt_template()
        template_str = template.template
        
        # Check for key components
        assert "UNSW CSE Open Day Assistant" in template_str
        assert "{context}" in template_str
        assert "{question}" in template_str
        assert "Sources" in template_str
        assert "INSUFFICIENT_CONTEXT" in template_str
        
    def test_rag_prompt_template_rendering(self):
        """Test RAG prompt template renders correctly with inputs"""
        template = PromptManager.get_rag_prompt_template()
        
        context = "COMP9900 is a capstone project course."
        question = "What is COMP9900?"
        
        rendered = template.format(context=context, question=question)
        
        assert context in rendered
        assert question in rendered
        assert "UNSW CSE Open Day Assistant" in rendered
        
    def test_get_rag_with_history_template_structure(self):
        """Test that RAG with history template has correct structure"""
        template = PromptManager.get_rag_with_history_template()
        
        assert isinstance(template, PromptTemplate)
        expected_vars = ["history", "context", "question"]
        assert all(var in template.input_variables for var in expected_vars)
        assert len(template.input_variables) == 3
        
    def test_get_rag_with_history_template_content(self):
        """Test that RAG with history template contains expected content"""
        template = PromptManager.get_rag_with_history_template()
        template_str = template.template
        
        # Check for key components
        assert "Welcome back" in template_str
        assert "{history}" in template_str
        assert "{context}" in template_str
        assert "{question}" in template_str
        assert "OUR CONVERSATION SO FAR" in template_str
        
    def test_rag_with_history_template_rendering(self):
        """Test RAG with history template renders correctly"""
        template = PromptManager.get_rag_with_history_template()
        
        history = "User: Hello\nAssistant: Hi! How can I help?"
        context = "COMP9900 is a capstone project course."
        question = "What are the prerequisites?"
        
        rendered = template.format(history=history, context=context, question=question)
        
        assert history in rendered
        assert context in rendered
        assert question in rendered
        assert "Welcome back" in rendered
        
    def test_get_query_rewrite_template(self):
        """Test query rewrite template structure and content"""
        template = PromptManager.get_query_rewrite_template()
        
        assert isinstance(template, str)
        assert "{history_context}" in template
        assert "{original_query}" in template
        assert "Query Enhancement Assistant" in template
        assert "REDIRECT:" in template
        assert "NAVIGATION_QUERY" in template
        
    def test_query_rewrite_template_examples(self):
        """Test that query rewrite template includes expected examples"""
        template = PromptManager.get_query_rewrite_template()
        
        # Check for example patterns
        assert "Tell me about COMP9020" in template
        assert "Where is J17?" in template
        assert "NAVIGATION_QUERY" in template
        assert "Compare COMP9900 and COMP9901" in template
        assert "University of Sydney" in template
        
    def test_get_fallback_prompt_template_structure(self):
        """Test fallback prompt template structure"""
        template = PromptManager.get_fallback_prompt_template()
        
        assert isinstance(template, PromptTemplate)
        expected_vars = ["question", "mazemap_context"]
        assert all(var in template.input_variables for var in expected_vars)
        assert len(template.input_variables) == 2
        
    def test_get_fallback_prompt_template_content(self):
        """Test fallback prompt template content"""
        template = PromptManager.get_fallback_prompt_template()
        template_str = template.template
        
        assert "{question}" in template_str
        assert "{mazemap_context}" in template_str
        assert "UNSW CSE Open Day Assistant" in template_str
        assert "Campus Navigation" in template_str
        
    def test_fallback_template_rendering(self):
        """Test fallback template renders correctly"""
        template = PromptManager.get_fallback_prompt_template()
        
        question = "Where is the library?"
        mazemap_context = "Interactive campus maps available"
        
        rendered = template.format(question=question, mazemap_context=mazemap_context)
        
        assert question in rendered
        assert mazemap_context in rendered
        
    def test_get_mazemap_context(self):
        """Test MazeMap context contains expected information"""
        context = PromptManager.get_mazemap_context()
        
        assert isinstance(context, str)
        assert "MazeMap" in context
        assert "use.mazemap.com" in context
        assert "J17" in context
        assert "Computer Science Building" in context
        assert "search=" in context


class TestPromptManagerEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_rag_prompt_with_empty_inputs(self):
        """Test RAG prompt with empty inputs"""
        template = PromptManager.get_rag_prompt_template()
        
        rendered = template.format(context="", question="")
        
        # Should still contain template structure
        assert "UNSW CSE Open Day Assistant" in rendered
        assert "Context:" in rendered
        assert "Question:" in rendered
        
    def test_rag_prompt_with_special_characters(self):
        """Test RAG prompt with special characters in inputs"""
        template = PromptManager.get_rag_prompt_template()
        
        context = "COMP9900: Advanced topics & practical applications (50% assessment)"
        question = "What's the assessment breakdown for COMP9900?"
        
        rendered = template.format(context=context, question=question)
        
        assert context in rendered
        assert question in rendered
        
    def test_history_template_with_empty_history(self):
        """Test history template with empty conversation history"""
        template = PromptManager.get_rag_with_history_template()
        
        rendered = template.format(history="", context="Test context", question="Test question")
        
        assert "Welcome back" in rendered
        assert "OUR CONVERSATION SO FAR:" in rendered
        
    def test_query_rewrite_template_formatting(self):
        """Test query rewrite template string formatting"""
        template = PromptManager.get_query_rewrite_template()
        
        # Test with empty history context
        formatted = template.format(history_context="", original_query="Test query")
        assert "Test query" in formatted
        
        # Test with history context
        history_context = "Previous discussion about COMP9900"
        formatted = template.format(history_context=history_context, original_query="Test query")
        assert history_context in formatted
        
    def test_fallback_template_with_empty_mazemap(self):
        """Test fallback template with empty MazeMap context"""
        template = PromptManager.get_fallback_prompt_template()
        
        rendered = template.format(question="Test question", mazemap_context="")
        
        assert "Test question" in rendered
        assert "Campus Navigation" in rendered


class TestPromptManagerIntegration:
    """Integration tests for prompt manager with realistic scenarios"""
    
    def test_course_inquiry_rag_prompt(self):
        """Test RAG prompt for course inquiry scenario"""
        template = PromptManager.get_rag_prompt_template()
        
        context = """
        COMP9900 Capstone Project
        This course provides students with the opportunity to undertake a substantial project
        in computer science. Prerequisites: COMP2511, COMP3311, and 96 units of credit.
        """
        question = "What are the prerequisites for COMP9900?"
        
        rendered = template.format(context=context, question=question)
        
        assert "COMP2511" in rendered
        assert "prerequisites" in rendered.lower()
        assert "96 units" in rendered
        
    def test_location_inquiry_fallback_prompt(self):
        """Test fallback prompt for location inquiry"""
        template = PromptManager.get_fallback_prompt_template()
        mazemap_context = PromptManager.get_mazemap_context()
        
        question = "Where is the Computer Science building?"
        
        rendered = template.format(question=question, mazemap_context=mazemap_context)
        
        assert "Computer Science building" in rendered
        assert "mazemap.com" in rendered
        assert "J17" in rendered
        
    def test_conversation_continuation_with_history(self):
        """Test conversation continuation with history template"""
        template = PromptManager.get_rag_with_history_template()
        
        history = """
        User: What is COMP9900?
        Assistant: COMP9900 is a capstone project course for computer science students.
        """
        context = "Prerequisites: COMP2511, COMP3311, 96 units of credit."
        question = "What are the prerequisites for it?"
        
        rendered = template.format(history=history, context=context, question=question)
        
        assert "capstone project" in rendered
        assert "COMP2511" in rendered
        assert "prerequisites for it" in rendered
        assert "previous discussion" in rendered.lower() or "conversation" in rendered.lower()
        
    def test_query_enhancement_scenarios(self):
        """Test query enhancement template with various scenarios"""
        template = PromptManager.get_query_rewrite_template()
        
        test_cases = [
            ("Tell me about COMP9900", "course information"),
            ("Where is J17?", "location query"),
            ("What about University of Sydney?", "non-UNSW redirect"),
            ("How do I get to the library?", "navigation query")
        ]
        
        for query, expected_type in test_cases:
            formatted = template.format(history_context="", original_query=query)
            assert query in formatted
            
            # Check that appropriate handling is mentioned
            if "University of Sydney" in query:
                assert "REDIRECT" in formatted
            elif "Where is" in query or "How do I get" in query:
                assert "NAVIGATION" in formatted


class TestPromptManagerConsistency:
    """Test consistency across different prompt templates"""
    
    def test_all_templates_have_assistant_branding(self):
        """Test that all templates include UNSW CSE branding"""
        templates = [
            PromptManager.get_rag_prompt_template().template,
            PromptManager.get_rag_with_history_template().template,
            PromptManager.get_query_rewrite_template(),
            PromptManager.get_fallback_prompt_template().template
        ]
        
        for template in templates:
            assert "UNSW" in template or "CSE" in template
            
    def test_all_templates_have_emoji_styling(self):
        """Test that all templates use consistent emoji styling"""
        templates = [
            PromptManager.get_rag_prompt_template().template,
            PromptManager.get_rag_with_history_template().template,
            PromptManager.get_query_rewrite_template(),
            PromptManager.get_fallback_prompt_template().template
        ]
        
        for template in templates:
            # Should contain emojis for friendly tone
            emoji_found = any(char in template for char in "🎓✨💡🔍📝⚡🎯")
            assert emoji_found, f"Template should contain emojis: {template[:100]}..."
            
    def test_source_attribution_consistency(self):
        """Test that source attribution format is consistent"""
        rag_template = PromptManager.get_rag_prompt_template().template
        history_template = PromptManager.get_rag_with_history_template().template
        
        # Both should mention sources format
        assert "Sources" in rag_template
        assert "Sources" in history_template
        
        # Should have consistent format
        source_format = "[Document Name](URL)"
        assert source_format in rag_template
        assert source_format in history_template