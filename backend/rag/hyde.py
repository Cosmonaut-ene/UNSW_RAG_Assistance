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

        # Note: deliberately does NOT ask the model to invent specific course
        # codes or other precise identifiers. HyDE only needs this text to be
        # embedded -- what matters is that its wording/style/structure matches
        # real UNSW documentation closely enough for the embedding to land near
        # real document vectors. Asking it to "contain specific course codes"
        # risks the model fabricating a wrong code, which would pull retrieval
        # toward an unrelated course instead of helping it.
        prompt = (
            "You are a knowledgeable UNSW Computer Science and Engineering assistant. "
            "Given the following question, write a detailed hypothetical answer as if you had "
            "access to the UNSW CSE knowledge base. Write in the same factual, formal style and "
            "terminology as official UNSW documentation (e.g. course descriptions, handbook entries), "
            "so it reads like a real document. Do NOT invent specific course codes, unit numbers, or "
            "other identifiers you cannot verify -- describe the topic in general, document-like "
            "language instead. Keep it to 2-3 sentences.\n\n"
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


def hyde_search(hyde_doc: str,
                search_fn,
                k: int = 10) -> list:
    """
    Perform HyDE-enhanced search: retrieve using the hypothetical document's
    embedding, which sits closer to real document embeddings than the short
    original query does.

    Note: this does NOT also search the original query — retrieve_node's main
    path (process_with_rag_detailed) already does that with the same
    underlying function. Searching it again here was pure duplicate work
    whose results were mostly discarded at the final content-based dedupe
    anyway.

    Args:
        hyde_doc: Generated hypothetical document
        search_fn: Function that takes (query, k) and returns list of documents
        k: Number of results to retrieve

    Returns:
        Deduplicated list of documents from the HyDE search
    """
    hyde_results = search_fn(hyde_doc, k=k)

    # Deduplicate by content prefix (search_fn can return overlapping chunks)
    seen = set()
    merged = []
    for doc in hyde_results:
        content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
        key = content[:150]
        if key not in seen:
            seen.add(key)
            merged.append(doc)

    print(f"[HyDE] HyDE search returned {len(hyde_results)} results, {len(merged)} unique")
    return merged
