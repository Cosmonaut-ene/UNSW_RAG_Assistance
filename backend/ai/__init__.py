# ai/__init__.py
"""
AI Module - Handles LLM interactions, prompt engineering, and response generation
"""

from .query_enhancer import analyze_query_with_context
from .response_generator import generate_response, generate_fallback_response
from .safety_checker import is_query_safe_by_gemini

__all__ = [
    'analyze_query_with_context',
    'generate_response',
    'generate_fallback_response',
    'is_query_safe_by_gemini',
]
