# rag/hyde.py
"""
HyDE (Hypothetical Document Embeddings) - Generates a hypothetical answer
to bridge the semantic gap between short queries and long documents.

Reference: Gao et al. "Precise Zero-Shot Dense Retrieval without Relevance Labels" (2023)
"""

from typing import Optional


def generate_hypothetical_document(query: str, conversation_history: str = "") -> Optional[str]:
    """
    Generate a hypothetical answer to the query using Gemini.
    This answer is used for embedding-based retrieval alongside the original query,
    improving recall for vague or short queries.

    Args:
        query: The user's (possibly rewritten) query
        conversation_history: Formatted conversation history

    Returns:
        A hypothetical answer string, or None on failure
    """
    try:
        from ai.llm_client import get_genai_model
        model = get_genai_model("gemini-2.5-flash")

        prompt = (
            "You are a knowledgeable UNSW Computer Science and Engineering assistant. "
            "Given the following question, write a detailed hypothetical answer as if you had "
            "access to the UNSW CSE knowledge base. The answer should be factual-sounding and "
            "contain specific details, course codes, and terminology that would appear in real "
            "UNSW documentation. Keep it to 2-3 sentences.\n\n"
            f"Question: {query}\n\n"
            "Hypothetical Answer:"
        )

        response = model.generate_content(prompt)
        hyde_doc = response.text.strip()

        if hyde_doc:
            print(f"[HyDE] Generated hypothetical document ({len(hyde_doc)} chars)")
            return hyde_doc
        return None

    except Exception as e:
        print(f"[HyDE] Error generating hypothetical document: {e}")
        return None


def hyde_search(query: str,
                hyde_doc: str,
                search_fn,
                k: int = 10) -> list:
    """
    Perform HyDE-enhanced search: retrieve using both the original query
    and the hypothetical document, then merge and deduplicate results.

    Args:
        query: Original query
        hyde_doc: Generated hypothetical document
        search_fn: Function that takes (query, k) and returns list of documents
        k: Number of results to retrieve per query

    Returns:
        Merged and deduplicated list of documents
    """
    # Search with original query
    original_results = search_fn(query, k=k)

    # Search with hypothetical document
    hyde_results = search_fn(hyde_doc, k=k)

    # Merge and deduplicate by content prefix
    seen = set()
    merged = []

    for doc in original_results:
        content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
        key = content[:150]
        if key not in seen:
            seen.add(key)
            merged.append(doc)

    for doc in hyde_results:
        content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
        key = content[:150]
        if key not in seen:
            seen.add(key)
            merged.append(doc)

    print(f"[HyDE] Merged results: {len(original_results)} original + {len(hyde_results)} hyde = {len(merged)} unique")
    return merged
