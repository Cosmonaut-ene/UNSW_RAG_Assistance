# rag/graph_rag.py
"""
LangGraph Agentic RAG - Graph-based orchestration for the RAG pipeline.
Replaces the if/elif chain in query_processor.py with a structured graph.

Graph flow:
  safety_check -> query_rewrite -> hyde_generate -> retrieve -> rerank
  -> grade_documents -> generate -> hallucination_check -> output

Fallback paths:
  - safety_check UNSAFE -> return warning
  - query_rewrite NAVIGATION -> fallback LLM
  - query_rewrite REDIRECT -> return warning
  - grade_documents INCORRECT -> fallback LLM
  - hallucination_check FAIL -> regenerate (max 1 retry)
"""

import time
from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph import StateGraph, END


# ===== State Definition =====

class RAGState(TypedDict):
    """State passed between graph nodes"""
    # Input
    query: str
    session_id: str
    history: str  # formatted conversation history
    conversation_history: list  # raw conversation history

    # Processing
    rewritten_query: str
    hyde_doc: str
    documents: List[Dict]
    reranked_docs: List[Dict]
    docs_relevant: bool

    # Output
    answer: str
    answered: bool
    matched_files: List[str]
    fallback: bool
    safety_blocked: bool
    processing_steps: List[str]

    # Control
    generation_attempts: int


# ===== Node Functions =====

def safety_check_node(state: RAGState) -> dict:
    """Check if the query is safe and appropriate"""
    steps = list(state.get("processing_steps", []))
    steps.append("safety_check")

    from ai.safety_checker import is_query_safe_by_gemini
    is_safe = is_query_safe_by_gemini(state["query"])

    if not is_safe:
        steps.append("safety_blocked")
        return {
            "safety_blocked": True,
            "answer": "I can only help with UNSW-related questions. Please ask about UNSW programs and courses.",
            "answered": True,
            "processing_steps": steps,
        }

    return {
        "safety_blocked": False,
        "processing_steps": steps,
    }


def query_rewrite_node(state: RAGState) -> dict:
    """Rewrite the query with conversation context"""
    steps = list(state.get("processing_steps", []))
    steps.append("query_rewriting")

    from ai.query_enhancer import rewrite_query_with_context
    conversation_history = state.get("conversation_history", [])
    rewritten = rewrite_query_with_context(state["query"], conversation_history)

    print(f"[GraphRAG] Original: {state['query']}")
    print(f"[GraphRAG] Rewritten: {rewritten}")

    return {
        "rewritten_query": rewritten,
        "processing_steps": steps,
    }


def hyde_generate_node(state: RAGState) -> dict:
    """Generate hypothetical document for improved retrieval"""
    steps = list(state.get("processing_steps", []))
    steps.append("hyde_generation")

    from rag.hyde import generate_hypothetical_document
    hyde_doc = generate_hypothetical_document(
        state.get("rewritten_query", state["query"]),
        state.get("history", "")
    )

    return {
        "hyde_doc": hyde_doc or "",
        "processing_steps": steps,
    }


def retrieve_node(state: RAGState) -> dict:
    """Retrieve documents using hybrid search (RAG + BM25) with HyDE"""
    steps = list(state.get("processing_steps", []))
    steps.append("retrieval")

    rewritten_query = state.get("rewritten_query", state["query"])
    hyde_doc = state.get("hyde_doc", "")

    # RAG search
    from rag import process_with_rag_detailed
    rag_result = process_with_rag_detailed(rewritten_query, state.get("conversation_history"))
    rag_search_results = rag_result.get("search_results", [])

    # Hybrid search (RAG + BM25)
    steps.append("hybrid_search")
    from rag.hybrid_search import HybridSearchEngine
    try:
        from rag import load_vector_store
        vector_store = load_vector_store()
    except Exception as e:
        print(f"[GraphRAG] Could not load vector store: {e}")
        vector_store = None

    hybrid_engine = HybridSearchEngine(
        vector_store=vector_store,
        min_hybrid_score=70.0,
        min_bm25_score=3.0,
        min_rag_score=25.0
    )

    hybrid_rag_results = [
        {"page_content": doc.get("page_content", ""), "metadata": doc.get("metadata", {})}
        for doc in rag_search_results
    ]

    hybrid_results = hybrid_engine.search_hybrid(rewritten_query, hybrid_rag_results, max_results=30)

    # If we have a HyDE doc, do additional search and merge
    if hyde_doc:
        steps.append("hyde_search")
        try:
            from rag.hyde import hyde_search
            from rag.search_engine import search_similar_documents

            hyde_extra = hyde_search(rewritten_query, hyde_doc, search_similar_documents, k=10)
            # Convert to dict format and add to results
            seen_content = set(r.get("page_content", "")[:100] for r in hybrid_results)
            for doc in hyde_extra:
                content = doc.page_content if hasattr(doc, "page_content") else ""
                if content[:100] not in seen_content:
                    seen_content.add(content[:100])
                    hybrid_results.append({
                        "page_content": content,
                        "metadata": doc.metadata if hasattr(doc, "metadata") else {}
                    })
        except Exception as e:
            print(f"[GraphRAG] HyDE search failed: {e}")

    print(f"[GraphRAG] Retrieved {len(hybrid_results)} total documents")

    return {
        "documents": hybrid_results,
        "processing_steps": steps,
    }


def rerank_node(state: RAGState) -> dict:
    """Rerank documents using cross-encoder"""
    steps = list(state.get("processing_steps", []))
    steps.append("reranking")

    documents = state.get("documents", [])
    rewritten_query = state.get("rewritten_query", state["query"])

    try:
        from rag.reranker import rerank_documents
        reranked = rerank_documents(rewritten_query, documents, top_k=7)
    except Exception as e:
        print(f"[GraphRAG] Reranking failed: {e}")
        reranked = documents[:7]

    # Extract matched files
    matched_files = []
    for doc in reranked:
        source = doc.get("metadata", {}).get("source", "")
        if source:
            filename = source.split("/")[-1] if "/" in source else source
            if filename and filename not in matched_files:
                matched_files.append(filename)

    return {
        "reranked_docs": reranked,
        "matched_files": matched_files,
        "processing_steps": steps,
    }


def grade_documents_node(state: RAGState) -> dict:
    """CRAG: Grade document relevance before generation"""
    steps = list(state.get("processing_steps", []))
    steps.append("crag_grading")

    reranked_docs = state.get("reranked_docs", [])
    rewritten_query = state.get("rewritten_query", state["query"])

    from rag.retrieval_evaluator import grade_documents
    grade, filtered_docs = grade_documents(rewritten_query, reranked_docs)

    docs_relevant = grade == "CORRECT"

    if not docs_relevant:
        steps.append("crag_incorrect")

    return {
        "docs_relevant": docs_relevant,
        "reranked_docs": filtered_docs if docs_relevant else reranked_docs,
        "processing_steps": steps,
    }


def generate_node(state: RAGState) -> dict:
    """Generate answer from retrieved context"""
    steps = list(state.get("processing_steps", []))
    steps.append("ai_generation")

    reranked_docs = state.get("reranked_docs", [])
    rewritten_query = state.get("rewritten_query", state["query"])
    history = state.get("history", "")

    from ai import process_query as ai_process_query

    # Convert to format expected by AI module
    search_results = [
        {"page_content": doc.get("page_content", ""), "metadata": doc.get("metadata", {})}
        for doc in reranked_docs
    ]

    ai_result = ai_process_query(rewritten_query, search_results, history)
    answer = ai_result.get("answer", "")
    safety_blocked = ai_result.get("safety_blocked", False)

    if safety_blocked:
        steps.append("safety_blocked_generation")

    # Update matched files from AI result
    matched_files = list(state.get("matched_files", []))
    for f in ai_result.get("matched_files", []):
        if f not in matched_files:
            matched_files.append(f)

    generation_attempts = state.get("generation_attempts", 0) + 1

    return {
        "answer": answer,
        "answered": True,
        "safety_blocked": safety_blocked,
        "matched_files": matched_files,
        "generation_attempts": generation_attempts,
        "processing_steps": steps,
    }


def fallback_node(state: RAGState) -> dict:
    """Direct LLM fallback when RAG context is insufficient"""
    steps = list(state.get("processing_steps", []))
    steps.append("fallback")

    rewritten_query = state.get("rewritten_query", state["query"])
    history = state.get("history", "")

    from ai.response_generator import generate_fallback_response
    fallback_answer = generate_fallback_response(rewritten_query, history)

    return {
        "answer": fallback_answer,
        "answered": True,
        "fallback": True,
        "matched_files": [],
        "processing_steps": steps,
    }


def hallucination_check_node(state: RAGState) -> dict:
    """Check if the generated answer might be hallucinated"""
    steps = list(state.get("processing_steps", []))
    steps.append("hallucination_check")

    answer = state.get("answer", "")

    # Simple heuristic checks for hallucination indicators
    hallucination_phrases = [
        "i don't have any information",
        "i don't know",
        "INSUFFICIENT_CONTEXT",
        "within the current context",
    ]

    is_hallucinated = False
    for phrase in hallucination_phrases:
        if phrase.lower() in answer.lower():
            is_hallucinated = True
            steps.append(f"hallucination_detected:{phrase[:20]}")
            break

    if not answer:
        is_hallucinated = True
        steps.append("hallucination_detected:empty_answer")

    return {
        "fallback": is_hallucinated,
        "processing_steps": steps,
    }


# ===== Routing Functions =====

def route_after_safety(state: RAGState) -> str:
    if state.get("safety_blocked"):
        return END
    return "query_rewrite"


def route_after_rewrite(state: RAGState) -> str:
    rewritten = state.get("rewritten_query", "")

    if rewritten.strip() == "NAVIGATION_QUERY":
        return "fallback"

    if rewritten.startswith("REDIRECT:") or "can only help with unsw-related questions" in rewritten.lower():
        return END

    return "hyde_generate"


def route_after_grading(state: RAGState) -> str:
    if not state.get("docs_relevant", True):
        return "fallback"
    if not state.get("reranked_docs"):
        return "fallback"
    return "generate"


def route_after_hallucination_check(state: RAGState) -> str:
    if state.get("fallback") and state.get("generation_attempts", 0) <= 1:
        return "fallback"
    return END


# ===== Graph Builder =====

def build_rag_graph() -> StateGraph:
    """
    Build the LangGraph RAG pipeline.

    Returns a compiled StateGraph that can be invoked with:
        result = graph.invoke(initial_state)
    """
    graph = StateGraph(RAGState)

    # Add nodes
    graph.add_node("safety_check", safety_check_node)
    graph.add_node("query_rewrite", query_rewrite_node)
    graph.add_node("hyde_generate", hyde_generate_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("rerank", rerank_node)
    graph.add_node("grade_documents", grade_documents_node)
    graph.add_node("generate", generate_node)
    graph.add_node("fallback", fallback_node)
    graph.add_node("hallucination_check", hallucination_check_node)

    # Set entry point
    graph.set_entry_point("safety_check")

    # Add edges
    graph.add_conditional_edges("safety_check", route_after_safety)
    graph.add_conditional_edges("query_rewrite", route_after_rewrite)
    graph.add_edge("hyde_generate", "retrieve")
    graph.add_edge("retrieve", "rerank")
    graph.add_edge("rerank", "grade_documents")
    graph.add_conditional_edges("grade_documents", route_after_grading)
    graph.add_edge("generate", "hallucination_check")
    graph.add_conditional_edges("hallucination_check", route_after_hallucination_check)
    graph.add_edge("fallback", END)

    return graph.compile()


# Module-level singleton
_compiled_graph = None


def get_rag_graph():
    """Get compiled RAG graph (singleton)"""
    global _compiled_graph
    if _compiled_graph is None:
        print("[GraphRAG] Building RAG graph...")
        _compiled_graph = build_rag_graph()
        print("[GraphRAG] RAG graph built successfully")
    return _compiled_graph


def invoke_rag_graph(query: str,
                     session_id: str = "",
                     conversation_history: list = None,
                     formatted_history: str = "") -> dict:
    """
    High-level API to invoke the RAG graph.

    Args:
        query: User question
        session_id: Session identifier
        conversation_history: Raw conversation history list
        formatted_history: Pre-formatted history string

    Returns:
        Dict with answer, answered, matched_files, and performance data
    """
    start_time = time.time()

    graph = get_rag_graph()

    initial_state: RAGState = {
        "query": query,
        "session_id": session_id or "",
        "history": formatted_history or "",
        "conversation_history": conversation_history or [],
        "rewritten_query": "",
        "hyde_doc": "",
        "documents": [],
        "reranked_docs": [],
        "docs_relevant": True,
        "answer": "",
        "answered": False,
        "matched_files": [],
        "fallback": False,
        "safety_blocked": False,
        "processing_steps": [],
        "generation_attempts": 0,
    }

    result = graph.invoke(initial_state)

    response_time = int((time.time() - start_time) * 1000)

    # Handle REDIRECT case from query rewrite
    rewritten = result.get("rewritten_query", "")
    if rewritten.startswith("REDIRECT:"):
        answer = rewritten[9:].strip()
        return {
            "answer": answer,
            "answered": True,
            "matched_files": [],
            "performance": {
                "response_time_ms": response_time,
                "processing_steps": result.get("processing_steps", []),
                "cache_hit": False,
                "warning_returned": True,
            }
        }

    return {
        "answer": result.get("answer", ""),
        "answered": result.get("answered", False),
        "matched_files": result.get("matched_files", []),
        "retrieved_contexts": [
            doc.get("page_content", "")
            for doc in result.get("reranked_docs", [])
            if doc.get("page_content", "").strip()
        ],
        "performance": {
            "response_time_ms": response_time,
            "processing_steps": result.get("processing_steps", []),
            "cache_hit": False,
            "fallback_used": result.get("fallback", False),
            "safety_blocked": result.get("safety_blocked", False),
        }
    }
