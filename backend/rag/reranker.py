# rag/reranker.py
"""
Cross-Encoder Reranker - Reranks retrieved documents using a cross-encoder model
Uses sentence-transformers cross-encoder/ms-marco-MiniLM-L-6-v2 for fast, accurate reranking
"""

import time
from typing import List, Dict, Optional

# Lazy-load the model to avoid startup cost
_cross_encoder = None
_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _get_cross_encoder():
    """Lazy-load the cross-encoder model (singleton)"""
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder
            print(f"[Reranker] Loading cross-encoder model: {_MODEL_NAME}")
            _cross_encoder = CrossEncoder(_MODEL_NAME)
            print(f"[Reranker] Cross-encoder model loaded successfully")
        except ImportError:
            print("[Reranker] sentence-transformers not installed. Run: pip install sentence-transformers")
            raise
        except Exception as e:
            print(f"[Reranker] Error loading cross-encoder model: {e}")
            raise
    return _cross_encoder


def rerank_documents(query: str,
                     documents: List[Dict],
                     top_k: int = 7,
                     content_key: str = "page_content") -> List[Dict]:
    """
    Rerank documents using cross-encoder model.

    Args:
        query: The user query
        documents: List of document dicts with 'page_content' or 'content' key
        top_k: Number of top documents to return after reranking
        content_key: Key to extract text content from documents

    Returns:
        Reranked list of documents (top_k), with 'rerank_score' added to metadata
    """
    if not documents:
        return []

    if len(documents) <= 1:
        return documents

    start_time = time.time()

    try:
        model = _get_cross_encoder()

        # Build query-document pairs for scoring
        pairs = []
        for doc in documents:
            content = doc.get(content_key, doc.get("content", ""))
            if not content:
                content = ""
            # Truncate very long content to avoid OOM (cross-encoder max ~512 tokens)
            if len(content) > 1500:
                content = content[:1500]
            pairs.append([query, content])

        # Score all pairs
        scores = model.predict(pairs)

        # Attach scores to documents
        scored_docs = []
        for doc, score in zip(documents, scores):
            doc_copy = dict(doc)
            if "metadata" not in doc_copy:
                doc_copy["metadata"] = {}
            doc_copy["metadata"]["rerank_score"] = float(score)
            scored_docs.append(doc_copy)

        # Sort by rerank score descending
        scored_docs.sort(key=lambda x: x["metadata"]["rerank_score"], reverse=True)

        elapsed = time.time() - start_time
        print(f"[Reranker] Reranked {len(documents)} docs in {elapsed*1000:.0f}ms, returning top {top_k}")

        # Log top results
        for i, doc in enumerate(scored_docs[:top_k]):
            source = doc.get("metadata", {}).get("source", "unknown")
            score = doc["metadata"]["rerank_score"]
            print(f"[Reranker]   #{i+1}: score={score:.4f} source={source}")

        return scored_docs[:top_k]

    except Exception as e:
        print(f"[Reranker] Error during reranking: {e}. Returning original order.")
        return documents[:top_k]
