# ai/__init__.py
"""
AI Module - Handles LLM interactions, prompt engineering, and response generation
"""

from .query_processor import enhance_query, rewrite_query_with_context
from .response_generator import generate_response, process_with_ai_pipeline, ask_with_hybrid_search, ask_with_rag_and_fallback
from .safety_checker import is_query_safe_by_gemini
# Removed direct rag dependency - HybridSearchEngine will be imported by services layer when needed

# Main public API
def process_query(question: str, search_results: list = None, formatted_history: str = "") -> dict:
    """
    Process user query with AI enhancement and generate response
    Note: This now expects pre-retrieved search results from the service layer
    
    Args:
        question: User's question
        search_results: Pre-retrieved search results from RAG/hybrid search
        formatted_history: Pre-formatted conversation history
        
    Returns:
        Dict with answer, sources, matched_files, and metadata
    """
    from .response_generator import process_with_ai_pipeline
    return process_with_ai_pipeline(question, search_results, formatted_history)

def check_query_safety(query: str) -> bool:
    """Check if query passes safety filters"""
    return is_query_safe_by_gemini(query)

# Export key classes and functions
__all__ = [
    'process_query',
    'check_query_safety', 
    'enhance_query',
    'generate_response',
    'process_with_ai_pipeline',
    'ask_with_hybrid_search',
    'ask_with_rag_and_fallback',
    # 'HybridSearchEngine' - now handled by services layer
]