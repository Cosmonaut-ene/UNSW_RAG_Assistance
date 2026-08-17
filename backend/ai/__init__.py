# ai/__init__.py
"""
AI Module - Handles LLM interactions, prompt engineering, and response generation
"""

from .query_enhancer import enhance_query, rewrite_query_with_context
from .response_generator import generate_response, generate_fallback_response
from .safety_checker import is_query_safe_by_gemini

__all__ = [
    'enhance_query',
    'rewrite_query_with_context',
    'generate_response',
    'generate_fallback_response',
    'is_query_safe_by_gemini',
]
