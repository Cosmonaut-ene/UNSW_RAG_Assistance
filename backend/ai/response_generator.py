# ai/response_generator.py
"""
Response Generator - Handles AI response generation and fallback logic
"""

from typing import Dict, List, Optional
from .llm_client import get_chat_llm
from .prompt_manager import PromptManager
from .safety_checker import is_query_safe_by_gemini
from .query_processor import rewrite_query_with_context
# Removed direct rag dependency - will be handled by services layer

def generate_response(context: str, question: str, formatted_history: str = "") -> str:
    """
    Generate response using LLM with given context
    
    Args:
        context: Retrieved context from RAG
        question: User's question
        formatted_history: Pre-formatted conversation history
        
    Returns:
        str: Generated response
    """
    
    llm = get_chat_llm()
    
    if formatted_history:
        template = PromptManager.get_rag_with_history_template()
        response = llm.invoke(template.format(
            history=formatted_history,
            context=context,
            question=question
        ))
    else:
        template = PromptManager.get_rag_prompt_template()
        response = llm.invoke(template.format(
            context=context,
            question=question
        ))
    
    return response.content if hasattr(response, 'content') else str(response)

def generate_fallback_response(question: str, formatted_history: str = "") -> str:
    """
    Generate fallback response when no context is available
    
    Args:
        question: User's question
        conversation_history: Previous conversation exchanges
        
    Returns:
        str: Fallback response with UNSW CSE assistant identity
    """
    # History formatting is now handled by the calling service layer
    
    mazemap_context = PromptManager.get_mazemap_context()
    llm = get_chat_llm()
    
    if formatted_history:
        # Use fallback template with history
        template = PromptManager.get_fallback_prompt_template()
        # Modify template to include history
        template_with_history = template.template.replace(
            "❓ Question: {question}",
            "== Conversation History ==\n{history}\n\n❓ Question: {question}"
        )
        template_with_history = template_with_history.replace(
            'input_variables=["question", "mazemap_context"]',
            'input_variables=["question", "mazemap_context", "history"]'
        )
        
        response = llm.invoke(template_with_history.format(
            history=formatted_history,
            question=question,
            mazemap_context=mazemap_context
        ))
    else:
        template = PromptManager.get_fallback_prompt_template()
        response = llm.invoke(template.format(
            question=question,
            mazemap_context=mazemap_context
        ))
    
    print("[AI Response] Using fallback direct LLM with UNSW CSE assistant identity")
    return response.content if hasattr(response, 'content') else str(response)

def process_with_ai_pipeline(question: str, search_results: List[Dict] = None, formatted_history: str = "") -> Dict:
    """
    AI processing pipeline: safety check, query rewrite, response generation
    Note: Search/retrieval is now handled by the calling service layer
    
    Args:
        question: User's question
        search_results: Pre-retrieved search results from RAG/hybrid search
        formatted_history: Pre-formatted conversation history
        
    Returns:
        Dict with answer, sources, matched_files, and metadata
    """
    print(f"[AI Pipeline] Processing question: {question}")
    
    # 1. Safety Check
    if not is_query_safe_by_gemini(question):
        return {
            "answer": "I cannot process this query as it may violate safety guidelines. Please rephrase your question.",
            "sources": [],
            "matched_files": [],
            "safety_blocked": True
        }
    
    # 2. Query Rewriting (if history is provided)
    if formatted_history:
        # Convert formatted history back to list format for query rewriting
        conversation_history = []
        lines = formatted_history.split('\n')
        current_q, current_a = None, None
        for line in lines:
            if line.startswith('用户: '):
                current_q = line[3:]
            elif line.startswith('助手: '):
                current_a = line[3:]
                if current_q and current_a:
                    conversation_history.append({'question': current_q, 'answer': current_a})
                    current_q, current_a = None, None
        
        rewritten_query = rewrite_query_with_context(question, conversation_history)
        print(f"[AI Pipeline] Rewritten query: {rewritten_query}")
    else:
        rewritten_query = question
    
    # 3. Generate Response from provided search results
    if not search_results:
        print("[AI Pipeline] No search results provided, using fallback")
        fallback_answer = generate_fallback_response(rewritten_query, formatted_history)
        return {
            "answer": fallback_answer,
            "sources": [],
            "matched_files": [],
            "safety_blocked": False
        }
    
    # Build context from search results
    context_parts = []
    for doc in search_results:
        context_parts.append(doc.get('page_content', ''))
    
    combined_context = '\n\n'.join(context_parts)
    
    # Generate final answer
    final_answer = generate_response(combined_context, rewritten_query, formatted_history)
    
    # Extract matched files
    matched_files = []
    source_details = []
    
    for doc in search_results:
        source_details.append(doc.get('page_content', ''))
        metadata = doc.get('metadata', {})
        source_file = metadata.get('source', 'Unknown')
        if source_file != 'Unknown':
            filename = source_file.split('/')[-1] if '/' in source_file else source_file
            if filename not in matched_files:
                matched_files.append(filename)
    
    print(f"[AI Pipeline] Generated response, matched files: {matched_files}")
    
    return {
        "answer": final_answer,
        "sources": source_details,
        "matched_files": matched_files,
        "safety_blocked": False,
        "search_type": "provided_results"
    }

# ========== Legacy Functions for Backward Compatibility ==========

def ask_with_hybrid_search(question: str, qa_chain, conversation_history: list = None) -> dict:
    """
    Answer questions using hybrid search (RAG + keyword) - backward compatibility function
    
    Args:
        question: User's question
        qa_chain: LangChain QA chain (for compatibility, but we use our own pipeline)
        conversation_history: Previous conversation exchanges
        
    Returns:
        Dict with answer, sources, matched_files, and metadata
    """
    print(f"[AI Response] Legacy hybrid search processing: {question}")
    
    # Import here to avoid circular dependency
    from services.query_processor import process_with_ai
    
    try:
        # Use the services layer to coordinate RAG + AI processing
        session_id = "legacy_hybrid_search"  # Dummy session for legacy calls
        answer, success, matched_files, metadata = process_with_ai(question, session_id)
        
        return {
            "answer": answer,
            "sources": [answer],  # Legacy format compatibility
            "matched_files": matched_files,
            "safety_blocked": metadata.get("safety_blocked", False),
            "search_type": "hybrid_legacy"
        }
    except Exception as e:
        print(f"[AI Response] Legacy hybrid search error: {e}")
        return {
            "answer": "I don't have information about that topic.",
            "sources": [],
            "matched_files": [],
            "safety_blocked": False,
            "search_type": "hybrid_legacy_error"
        }

def ask_with_rag_and_fallback(question: str, qa_chain, conversation_history: list = None) -> dict:
    """
    Try answering via RAG first, fallback to direct LLM - backward compatibility
    Note: Now delegates to services layer for proper coordination
    
    Args:
        question: User's question
        qa_chain: LangChain QA chain (for compatibility, not used)
        conversation_history: Previous conversation exchanges
        
    Returns:
        Dict with answer, sources, matched_files, and metadata
    """
    print(f"[AI Response] Legacy RAG with fallback - delegating to services layer: {question}")
    
    # Import here to avoid circular dependency
    from services.query_processor import process_with_ai
    
    try:
        # Use the services layer to coordinate RAG + AI processing
        session_id = "legacy_rag_fallback"  # Dummy session for legacy calls
        answer, success, matched_files, metadata = process_with_ai(question, session_id)
        
        return {
            "answer": answer,
            "sources": [answer],  # Legacy format compatibility
            "matched_files": matched_files,
            "safety_blocked": metadata.get("safety_blocked", False),
            "search_type": "rag_fallback_legacy"
        }
    except Exception as e:
        print(f"[AI Response] Legacy RAG fallback error: {e}")
        return {
            "answer": "I don't have information about that topic.",
            "sources": [],
            "matched_files": [],
            "safety_blocked": False,
            "search_type": "rag_fallback_legacy_error"
        }