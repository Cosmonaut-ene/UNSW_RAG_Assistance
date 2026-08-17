# ai/response_generator.py
"""
Response Generator - Handles AI response generation and fallback logic
"""

from typing import Dict, List, Tuple
from .llm_client import get_chat_llm
from .prompt_manager import PromptManager
# Removed direct rag dependency - will be handled by services layer


def build_context_and_sources(search_results: List[Dict]) -> Tuple[str, List[str]]:
    """
    Build the combined context string (with source metadata) and the list of
    matched filenames from a list of retrieved documents.

    Args:
        search_results: List of document dicts with 'page_content' and 'metadata'

    Returns:
        Tuple of (combined_context, matched_files)
    """
    context_parts = []
    source_info = []
    matched_files = []

    for i, doc in enumerate(search_results, 1):
        metadata = doc.get('metadata', {})
        source = metadata.get('source', 'Unknown')
        chunk_content = doc.get('page_content', '')
        # Numbered delimiters so each retrieved chunk is a clearly bounded
        # block of data, not text that blends into the surrounding prompt
        # (see the "content is reference only" instruction in the templates
        # that consume this -- C2 in SPEC.md, indirect prompt injection defense)
        context_parts.append(f"--- Retrieved Document {i} ---\n{chunk_content}")

        if source != 'Unknown':
            filename = source.split('/')[-1] if '/' in source else source
            if filename not in matched_files:
                matched_files.append(filename)

            if source.endswith('.pdf'):
                doc_name = filename.replace('.pdf', '').replace('_', ' ')
                source_info.append(f"Source: {doc_name} -> /docs/{filename}")
            else:
                doc_name = metadata.get('title', filename)
                source_info.append(f"Source: {doc_name} -> {source}")

    combined_context = '\n\n'.join(context_parts)
    if source_info:
        combined_context += "\n\n=== SOURCE METADATA ===\n" + '\n'.join(source_info)

    return combined_context, matched_files


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
    
    try:
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
    except Exception as e:
        print(f"[AI Response] Error in fallback response generation: {e}")
        return "I'm here to help with UNSW CSE related questions. Could you please rephrase your question?"
    
    print("[AI Response] Using fallback direct LLM with UNSW CSE assistant identity")
    
    # Handle response extraction with error handling
    try:
        if hasattr(response, 'content'):
            result = response.content
            # Handle empty or None content
            if not result:
                result = "I'm here to help with UNSW CSE related questions. Could you please rephrase your question?"
            return result
        else:
            result = str(response)
            if not result or result.lower() in ['none', 'null', '']:
                result = "I'm here to help with UNSW CSE related questions. Could you please rephrase your question?"
            return result
    except Exception as e:
        print(f"[AI Response] Error extracting response content: {e}")
        return "I'm here to help with UNSW CSE related questions. Could you please rephrase your question?"
