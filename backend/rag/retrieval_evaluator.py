# rag/retrieval_evaluator.py
"""
CRAG (Corrective RAG) - Evaluates whether each retrieved document is
relevant to the query before sending them to the generator.

Reference: Yan et al. "Corrective Retrieval Augmented Generation" (2024)

Grades:
  - CORRECT: at least one document is relevant, proceed to generation
             with only the relevant documents
  - INCORRECT: no documents are relevant, skip generation and use fallback
"""

import json
from typing import List, Dict, Tuple

# Per-chunk truncation for the relevance-grading prompt. text_splitter.py's
# target_chunk_size is 600 chars, so 700 covers the large majority of real
# chunks in full while keeping the combined prompt size bounded even when
# grading all ~12 reranked documents in a single call (unlike rerank.py's
# 1500-char truncation, which is sized for scoring one chunk at a time and
# rarely triggers against 600-char chunks anyway).
CHUNK_TRUNCATION_LENGTH = 700

GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "relevance": {
            "type": "array",
            "items": {"type": "boolean"},
        }
    },
    "required": ["relevance"],
}


def grade_documents(query: str,
                    documents: List[Dict],
                    content_key: str = "page_content") -> Tuple[str, List[Dict]]:
    """
    Grade each retrieved document's relevance to the query individually,
    using a single structured Gemini call covering every document (not just
    a sample of them).

    Args:
        query: The user query
        documents: List of document dicts with page_content
        content_key: Key for document text content

    Returns:
        Tuple of (grade, filtered_documents) where grade is "CORRECT" (at
        least one document kept) or "INCORRECT" (none kept), and
        filtered_documents contains only the documents judged relevant.
    """
    if not documents:
        print("[CRAG] No documents to grade")
        return "INCORRECT", []

    try:
        from ai.llm_client import get_genai_model
        model = get_genai_model("gemini-2.5-flash")

        snippets = []
        for i, doc in enumerate(documents):
            content = doc.get(content_key, doc.get("content", ""))
            snippet = content[:CHUNK_TRUNCATION_LENGTH] if content else "(empty)"
            snippets.append(f"[{i}] {snippet}")

        context_text = "\n\n".join(snippets)

        prompt = (
            "You are evaluating whether each retrieved document is relevant to a user's question.\n\n"
            f"Question: {query}\n\n"
            f"Retrieved Documents:\n{context_text}\n\n"
            f"For EACH of the {len(documents)} documents above (in the order given), judge whether it "
            "contains information relevant to answering the question. Return one boolean per document, "
            "in the same order -- the output array length must match the number of documents."
        )

        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": GRADE_SCHEMA,
            },
        )
        result = json.loads(response.text)
        relevance = result.get("relevance", [])

        if len(relevance) != len(documents):
            print(
                f"[CRAG] Relevance array length mismatch ({len(relevance)} vs {len(documents)} docs) "
                "-- padding/truncating rather than misaligning judgments to documents"
            )
            relevance = (list(relevance) + [False] * len(documents))[:len(documents)]

        filtered_docs = [doc for doc, keep in zip(documents, relevance) if keep]
        grade = "CORRECT" if filtered_docs else "INCORRECT"

        kept = len(filtered_docs)
        print(f"[CRAG] {kept}/{len(documents)} documents graded relevant for query: {query[:50]}...")

        return grade, filtered_docs

    except Exception as e:
        print(f"[CRAG] Error grading documents: {e}. Defaulting to CORRECT (fail open).")
        # Default to CORRECT on error to avoid blocking valid queries -- keep
        # all documents unfiltered rather than guessing which ones to drop.
        return "CORRECT", documents
