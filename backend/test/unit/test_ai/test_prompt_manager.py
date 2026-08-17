"""
Unit tests for AI Prompt Manager module
Tests prompt templates and engineering functionality

D2 in SPEC.md: get_rag_prompt_template and get_rag_with_history_template
used to be two ~90%-duplicated templates that could (and did) drift out of
sync -- particularly on the INSUFFICIENT_CONTEXT policy, where they gave
contradictory instructions. They're now one template with a conditional
{history_section}, same pattern query_rewrite's history_context already used.
"""

import pytest
from langchain_core.prompts import PromptTemplate

from ai.prompt_manager import PromptManager


class TestPromptManager:
    """Test prompt template management and rendering"""

    def test_get_rag_prompt_template_structure(self):
        """Test that the unified RAG prompt template has correct structure"""
        template = PromptManager.get_rag_prompt_template()

        assert isinstance(template, PromptTemplate)
        assert "context" in template.input_variables
        assert "question" in template.input_variables
        assert "history_section" in template.input_variables
        assert len(template.input_variables) == 3

    def test_get_rag_prompt_template_content(self):
        """Test that RAG prompt template contains expected content"""
        template = PromptManager.get_rag_prompt_template()
        template_str = template.template

        # Check for key components
        assert "UNSW CSE Open Day Assistant" in template_str
        assert "{context}" in template_str
        assert "{question}" in template_str
        assert "{history_section}" in template_str
        assert "Sources" in template_str
        assert "INSUFFICIENT_CONTEXT" in template_str

    def test_rag_prompt_template_rendering_without_history(self):
        """Test RAG prompt template renders correctly with an empty history section"""
        template = PromptManager.get_rag_prompt_template()

        context = "COMP9900 is a capstone project course."
        question = "What is COMP9900?"

        rendered = template.format(context=context, question=question, history_section="")

        assert context in rendered
        assert question in rendered
        assert "UNSW CSE Open Day Assistant" in rendered

    def test_rag_prompt_template_rendering_with_history(self):
        """Test RAG prompt template renders correctly with a populated history section"""
        template = PromptManager.get_rag_prompt_template()

        context = "Prerequisites: COMP2511, COMP3311, 96 units of credit."
        question = "What are the prerequisites for it?"
        history_section = "## 💬 OUR CONVERSATION SO FAR:\nUser: What is COMP9900?\nAssistant: A capstone project course.\n\n"

        rendered = template.format(context=context, question=question, history_section=history_section)

        assert context in rendered
        assert question in rendered
        assert "OUR CONVERSATION SO FAR" in rendered

    def test_get_query_rewrite_template(self):
        """Test query rewrite template structure and content (C3: merged with HyDE, REDIRECT removed)"""
        template = PromptManager.get_query_rewrite_template()

        assert isinstance(template, str)
        assert "{history_context}" in template
        assert "{original_query}" in template
        assert "Query Analysis Assistant" in template
        # REDIRECT is gone -- off-topic judgment now belongs to safety_check_node (C1)
        assert "REDIRECT:" not in template
        assert "NAVIGATION" in template
        # HyDE instructions now live in this template (C3)
        assert "hypothetical" in template.lower()
        assert "do not invent" in template.lower()

    def test_query_rewrite_template_examples(self):
        """Test that query rewrite template includes expected examples"""
        template = PromptManager.get_query_rewrite_template()

        # Check for example patterns
        assert "Tell me about COMP9020" in template
        assert "Where is J17?" in template
        assert "NAVIGATION" in template
        assert "Compare COMP9900 and COMP9901" in template

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


class TestPromptManagerInsufficientContextPolicy:
    """
    D2 in SPEC.md: generate_node must answer using ONLY the provided
    context, and emit INSUFFICIENT_CONTEXT (not its own general knowledge)
    when that context doesn't support an answer. The two old templates
    disagreed with each other on this exact point.
    """

    def test_policy_forbids_using_general_knowledge(self):
        template_str = PromptManager.get_rag_prompt_template().template

        assert "do not" in template_str.lower() or "do NOT" in template_str
        assert "general knowledge" in template_str.lower()

    def test_policy_is_a_single_unambiguous_rule(self):
        """There must be exactly one CONTEXT EVALUATION instruction, not two conflicting ones"""
        template_str = PromptManager.get_rag_prompt_template().template

        assert template_str.count("CONTEXT EVALUATION") == 1

    def test_insufficient_context_sentinel_present(self):
        template_str = PromptManager.get_rag_prompt_template().template

        assert "INSUFFICIENT_CONTEXT" in template_str


class TestPromptManagerEdgeCases:
    """Test edge cases and error scenarios"""

    def test_rag_prompt_with_empty_inputs(self):
        """Test RAG prompt with empty inputs"""
        template = PromptManager.get_rag_prompt_template()

        rendered = template.format(context="", question="", history_section="")

        # Should still contain template structure
        assert "UNSW CSE Open Day Assistant" in rendered
        assert "BEGIN RETRIEVED CONTEXT" in rendered
        assert "Question:" in rendered

    def test_rag_prompt_with_special_characters(self):
        """Test RAG prompt with special characters in inputs"""
        template = PromptManager.get_rag_prompt_template()

        context = "COMP9900: Advanced topics & practical applications (50% assessment)"
        question = "What's the assessment breakdown for COMP9900?"

        rendered = template.format(context=context, question=question, history_section="")

        assert context in rendered
        assert question in rendered

    def test_empty_history_section_omits_conversation_heading(self):
        """When there's no history, the section should just be an empty string, not a stray heading"""
        template = PromptManager.get_rag_prompt_template()

        rendered = template.format(context="Test context", question="Test question", history_section="")

        # No conversation heading should appear when history_section is empty
        assert "OUR CONVERSATION SO FAR" not in rendered

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

        rendered = template.format(context=context, question=question, history_section="")

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
        """Test conversation continuation via the unified template's history_section"""
        template = PromptManager.get_rag_prompt_template()

        history_section = (
            "## 💬 OUR CONVERSATION SO FAR:\n"
            "User: What is COMP9900?\n"
            "Assistant: COMP9900 is a capstone project course for computer science students.\n\n"
        )
        context = "Prerequisites: COMP2511, COMP3311, 96 units of credit."
        question = "What are the prerequisites for it?"

        rendered = template.format(context=context, question=question, history_section=history_section)

        assert "capstone project" in rendered
        assert "COMP2511" in rendered
        assert "prerequisites for it" in rendered
        assert "conversation" in rendered.lower()

    def test_query_enhancement_scenarios(self):
        """Test query enhancement template with various scenarios.

        Off-topic redirect (e.g. 'University of Sydney') is no longer this
        template's concern -- safety_check_node handles OFF_TOPIC classification
        before a query ever reaches query_rewrite (C1/C3 in SPEC.md)."""
        template = PromptManager.get_query_rewrite_template()

        test_cases = [
            ("Tell me about COMP9900", "course information"),
            ("Where is J17?", "location query"),
            ("How do I get to the library?", "navigation query")
        ]

        for query, expected_type in test_cases:
            formatted = template.format(history_context="", original_query=query)
            assert query in formatted

            # Check that appropriate handling is mentioned
            if "Where is" in query or "How do I get" in query:
                assert "NAVIGATION" in formatted


class TestPromptManagerConsistency:
    """Test consistency across different prompt templates"""

    def test_all_templates_have_assistant_branding(self):
        """Test that all templates include UNSW CSE branding"""
        templates = [
            PromptManager.get_rag_prompt_template().template,
            PromptManager.get_query_rewrite_template(),
            PromptManager.get_fallback_prompt_template().template
        ]

        for template in templates:
            assert "UNSW" in template or "CSE" in template

    def test_all_templates_have_emoji_styling(self):
        """Test that all templates use consistent emoji styling"""
        templates = [
            PromptManager.get_rag_prompt_template().template,
            PromptManager.get_query_rewrite_template(),
            PromptManager.get_fallback_prompt_template().template
        ]

        for template in templates:
            # Should contain emojis for friendly tone
            emoji_found = any(char in template for char in "🎓✨💡🔍📝⚡🎯")
            assert emoji_found, f"Template should contain emojis: {template[:100]}..."

    def test_source_attribution_format(self):
        """Test that source attribution format is present and consistent"""
        rag_template = PromptManager.get_rag_prompt_template().template

        assert "Sources" in rag_template
        assert "[Document Name](URL)" in rag_template


class TestPromptManagerInjectionDefense:
    """
    The RAG template must clearly mark retrieved context as reference
    data, not instructions -- defense against indirect prompt injection
    via a poisoned knowledge base document (C2 in SPEC.md).
    """

    def test_rag_template_declares_context_is_not_instructions(self):
        template = PromptManager.get_rag_prompt_template().template

        assert "not instructions" in template.lower()

    def test_rag_template_has_clear_context_boundary_markers(self):
        template = PromptManager.get_rag_prompt_template().template

        assert "BEGIN RETRIEVED CONTEXT" in template
        assert "END RETRIEVED CONTEXT" in template
