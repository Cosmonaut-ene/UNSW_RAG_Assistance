# rag/retrieval_evaluator.py
"""
CRAG (Corrective RAG) - Evaluates whether retrieved documents are relevant
to the query before sending them to the generator.

Reference: Yan et al. "Corrective Retrieval Augmented Generation" (2024)

Grades:
  - CORRECT: Documents are relevant, proceed to generation
  - INCORRECT: Documents are NOT relevant, skip generation and use fallback
"""

from typing import List, Dict, Tuple


def grade_documents(query: str,
                    documents: List[Dict],
                    content_key: str = "page_content") -> Tuple[str, List[Dict]]:
    """
    Grade whether retrieved documents are relevant to the query using Gemini.

    Args:
        query: The user query
        documents: List of document dicts with page_content
        content_key: Key for document text content

    Returns:
        Tuple of (grade, filtered_documents) where grade is "CORRECT" or "INCORRECT"
    """
    if not documents:
        print("[CRAG] No documents to grade")
        return "INCORRECT", []

    try:
        from ai.llm_client import get_genai_model
        model = get_genai_model("gemini-2.5-flash")

        # Build context snippets from top documents
        snippets = []
        for i, doc in enumerate(documents[:5]):  # Only check top 5
            content = doc.get(content_key, doc.get("content", ""))
            if content:
                snippets.append(f"Document {i+1}: {content[:300]}")

        context_text = "\n\n".join(snippets)

        prompt = (
            "You are evaluating whether retrieved documents are relevant to a user's question.\n\n"
            f"Question: {query}\n\n"
            f"Retrieved Documents:\n{context_text}\n\n"
            "Are these documents relevant enough to answer the question? "
            "Respond with exactly one word: CORRECT if at least some documents contain "
            "relevant information, or INCORRECT if none of the documents are relevant.\n\n"
            "Grade:"
        )

        response = model.generate_content(prompt)
        grade = response.text.strip().upper()

        if "INCORRECT" in grade:
            print(f"[CRAG] Documents graded as INCORRECT for query: {query[:50]}...")
            return "INCORRECT", []
        else:
            print(f"[CRAG] Documents graded as CORRECT for query: {query[:50]}...")
            return "CORRECT", documents

    except Exception as e:
        print(f"[CRAG] Error grading documents: {e}. Defaulting to CORRECT.")
        # Default to CORRECT on error to avoid blocking valid queries
        return "CORRECT", documents
