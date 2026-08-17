# ai/response_generator.py
"""
Response Generator - Handles AI response generation and fallback logic
"""

from typing import Dict, List, Tuple
from .llm_client import get_chat_llm
from .prompt_manager import PromptManager
# Removed direct rag dependency - will be handled by services layer

DEFAULT_FALLBACK_MESSAGE = "I'm here to help with UNSW CSE related questions. Could you please rephrase your question?"


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
    Generate response using LLM with given context.

    Uses a single unified template (D2 in SPEC.md) with a conditional
    history section, rather than picking between two separately-maintained
    templates that could (and did) drift out of sync with each other.

    Args:
        context: Retrieved context from RAG
        question: User's question
        formatted_history: Pre-formatted conversation history

    Returns:
        str: Generated response
    """
    llm = get_chat_llm()
    template = PromptManager.get_rag_prompt_template()

    history_section = ""
    if formatted_history:
        history_section = (
            "## 💬 OUR CONVERSATION SO FAR:\n"
            f"{formatted_history}\n\n"
        )

    response = llm.invoke(template.format(
        context=context,
        question=question,
        history_section=history_section,
    ))

    return response.content if hasattr(response, 'content') else str(response)

def generate_fallback_response(question: str, formatted_history: str = "", reason: str = "") -> str:
    """
    Generate fallback response when no context is available.

    Args:
        question: User's question
        formatted_history: Pre-formatted conversation history
        reason: Why fallback was triggered -- "navigation", "no_relevant_docs",
                or "hallucination_retry" (see RAGState.fallback_reason in
                graph_rag.py). Only "navigation" gets the MazeMap
                instructions injected; the other two reasons have nothing
                to do with campus locations, and including that whole
                section for them was pure noise that could nudge the model
                toward offering directions for an unrelated question (E2
                in SPEC.md).

    Returns:
        str: Fallback response with UNSW CSE assistant identity
    """
    try:
        llm = get_chat_llm()
        template = PromptManager.get_fallback_prompt_template()

        history_section = ""
        if formatted_history:
            history_section = (
                "## 💬 OUR CONVERSATION SO FAR:\n"
                f"{formatted_history}\n\n"
            )

        navigation_section = ""
        if reason == "navigation":
            navigation_section = (
                "🗺️ **Campus Navigation:**\n"
                f"{PromptManager.get_mazemap_context()}\n\n"
            )

        response = llm.invoke(template.format(
            question=question,
            history_section=history_section,
            navigation_section=navigation_section,
        ))
    except Exception as e:
        print(f"[AI Response] Error in fallback response generation: {e}")
        return DEFAULT_FALLBACK_MESSAGE

    print(f"[AI Response] Using fallback direct LLM with UNSW CSE assistant identity (reason={reason or 'unspecified'})")

    # Handle response extraction with error handling
    try:
        if hasattr(response, 'content'):
            result = response.content
            # Handle empty or None content
            if not result:
                result = DEFAULT_FALLBACK_MESSAGE
            return result
        else:
            result = str(response)
            if not result or result.lower() in ['none', 'null', '']:
                result = DEFAULT_FALLBACK_MESSAGE
            return result
    except Exception as e:
        print(f"[AI Response] Error extracting response content: {e}")
        return DEFAULT_FALLBACK_MESSAGE
