# rag/graph_rag.py
"""
LangGraph Agentic RAG - Graph-based orchestration for the RAG pipeline.
Replaces the if/elif chain in query_processor.py with a structured graph.

Graph flow:
  safety_and_rewrite -> retrieve -> rerank
  -> grade_documents -> generate -> hallucination_check -> output

safety_and_rewrite runs the safety classification and the query
rewrite+HyDE call concurrently (two threads, one node) rather than as two
sequential graph nodes -- both only need the original query + history and
don't depend on each other's output, so there was no reason to pay for two
back-to-back Gemini round trips on every request (previously separate
safety_check_node -> query_rewrite_node nodes; see SPEC.md perf notes).
query_rewrite also produces the HyDE hypothetical document in the same
structured call (previously a separate hyde_generate node/LLM call -- see
C3 in SPEC.md). Off-topic queries are rejected by the safety half of this
node itself (OFF_TOPIC classification, C1) and never reach retrieve at all.

Fallback paths:
  - safety check not SAFE -> return warning
  - query rewrite NAVIGATION intent -> fallback LLM
  - grade_documents INCORRECT -> fallback LLM
  - hallucination_check detects a problem -> fallback LLM (one-shot; despite
    generation_attempts existing, there is no actual "regenerate with the
    same context and recheck" loop -- fallback_node is a dead end straight
    to END, see D3 in SPEC.md)
"""

import time
from concurrent.futures import ThreadPoolExecutor
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
    query_intent: str  # "REWRITE" or "NAVIGATION", set by safety_and_rewrite_node
    documents: List[Dict]
    reranked_docs: List[Dict]
    fallback_reason: str  # "navigation" | "no_relevant_docs" | "hallucination_retry" -- which of the three paths into fallback_node fired (E2 in SPEC.md)

    # Output
    answer: str
    answered: bool
    matched_files: List[str]
    hallucination_detected: bool  # set by hallucination_check_node
    fallback_used: bool  # set by fallback_node -- was conflated with hallucination_detected before D3
    safety_blocked: bool
    processing_steps: List[str]

    # Control
    generation_attempts: int


# ===== Node Functions =====

def safety_and_rewrite_node(state: RAGState) -> dict:
    """
    Classify query safety and produce the rewritten query + HyDE doc in
    parallel (two threads, one node). Both calls only need the original
    query + history as input and don't depend on each other's output --
    previously two sequential graph nodes/LLM round trips, which meant
    every request paid for both latencies back to back even though
    neither result was needed to start the other call.

    If the query is unsafe, the rewrite/HyDE work is simply discarded
    (its cost was already paid by running concurrently, not added on top).
    """
    steps = list(state.get("processing_steps", []))
    steps.append("safety_check")
    steps.append("query_rewriting")

    from ai.safety_checker import is_query_safe_by_gemini
    from ai.query_enhancer import analyze_query_with_context

    query = state["query"]
    conversation_history = state.get("conversation_history", [])

    with ThreadPoolExecutor(max_workers=2) as executor:
        safety_future = executor.submit(is_query_safe_by_gemini, query)
        rewrite_future = executor.submit(analyze_query_with_context, query, conversation_history)
        is_safe = safety_future.result()
        result = rewrite_future.result()

    if not is_safe:
        steps.append("safety_blocked")
        return {
            "safety_blocked": True,
            "answer": "I can only help with UNSW-related questions. Please ask about UNSW programs and courses.",
            "answered": True,
            "processing_steps": steps,
        }

    print(f"[GraphRAG] Original: {query}")
    print(f"[GraphRAG] Intent: {result['intent']}, Rewritten: {result['rewritten_query']}")

    return {
        "safety_blocked": False,
        "rewritten_query": result["rewritten_query"],
        "hyde_doc": result["hypothetical_document"],
        "query_intent": result["intent"],
        "fallback_reason": "navigation" if result["intent"] == "NAVIGATION" else "",
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
    from config.rag_config import RAG_CONFIG
    try:
        from rag import load_vector_store
        vector_store = load_vector_store()
    except Exception as e:
        print(f"[GraphRAG] Could not load vector store: {e}")
        vector_store = None

    # No thresholds/weights passed explicitly -- HybridSearchEngine's own
    # defaults already come from RAG_CONFIG (E1), so there's nothing to
    # override here and no way for this call site to drift from it again.
    hybrid_engine = HybridSearchEngine(vector_store=vector_store)

    hybrid_rag_results = [
        {"page_content": doc.get("page_content", ""), "metadata": doc.get("metadata", {})}
        for doc in rag_search_results
    ]

    hybrid_results = hybrid_engine.search_hybrid(rewritten_query, hybrid_rag_results, max_results=RAG_CONFIG.max_hybrid_results)

    # If we have a HyDE doc, do additional search and merge
    if hyde_doc:
        steps.append("hyde_search")
        try:
            from rag.hyde import hyde_search
            from rag.search_engine import search_similar_documents

            hyde_extra = hyde_search(hyde_doc, search_similar_documents, k=RAG_CONFIG.hyde_search_k)
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

    from config.rag_config import RAG_CONFIG
    try:
        from rag.reranker import rerank_documents
        # top_k not passed -- rerank_documents() defaults to RAG_CONFIG.reranker_top_k itself (E1)
        reranked = rerank_documents(rewritten_query, documents)
    except Exception as e:
        print(f"[GraphRAG] Reranking failed: {e}")
        reranked = documents[:RAG_CONFIG.reranker_top_k]

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
    """
    CRAG: grade each reranked document's relevance individually, keeping
    only those judged relevant (D1 in SPEC.md). Previously only the top 5
    of up to 12 reranked documents were evaluated, yet all 12 were approved
    regardless of the verdict -- this now covers every document, and the
    filtered list actually reflects the grading instead of being all-or-nothing.
    """
    steps = list(state.get("processing_steps", []))
    steps.append("crag_grading")

    reranked_docs = state.get("reranked_docs", [])
    rewritten_query = state.get("rewritten_query", state["query"])

    from rag.retrieval_evaluator import grade_documents
    grade, filtered_docs = grade_documents(rewritten_query, reranked_docs)

    result = {
        "reranked_docs": filtered_docs,
        "processing_steps": steps,
    }

    if grade == "INCORRECT":
        steps.append("crag_incorrect")
        result["fallback_reason"] = "no_relevant_docs"

    return result


def generate_node(state: RAGState) -> dict:
    """
    Generate answer from retrieved context.

    Calls generate_response() directly rather than going through the old
    process_with_ai_pipeline() -- that function re-ran its own safety check
    and query rewrite internally, duplicating work safety_and_rewrite_node
    already did upstream in this graph (two extra LLM calls per request,
    and a second, independent safety verdict that could silently disagree
    with the first).
    """
    steps = list(state.get("processing_steps", []))
    steps.append("ai_generation")

    reranked_docs = state.get("reranked_docs", [])
    rewritten_query = state.get("rewritten_query", state["query"])
    history = state.get("history", "")

    from ai.response_generator import generate_response, build_context_and_sources

    search_results = [
        {"page_content": doc.get("page_content", ""), "metadata": doc.get("metadata", {})}
        for doc in reranked_docs
    ]

    combined_context, context_matched_files = build_context_and_sources(search_results)
    answer = generate_response(combined_context, rewritten_query, history)

    matched_files = list(state.get("matched_files", []))
    for f in context_matched_files:
        if f not in matched_files:
            matched_files.append(f)

    generation_attempts = state.get("generation_attempts", 0) + 1

    return {
        "answer": answer,
        "answered": True,
        "matched_files": matched_files,
        "generation_attempts": generation_attempts,
        "processing_steps": steps,
    }


def fallback_node(state: RAGState) -> dict:
    """
    Direct LLM fallback when RAG context is insufficient. Reached from
    three different triggers (query_rewrite NAVIGATION intent /
    grade_documents no relevant docs / hallucination_check detected a
    problem) -- fallback_reason (set by whichever of those fired) decides
    whether the MazeMap navigation instructions belong in the prompt at
    all (E2 in SPEC.md).
    """
    steps = list(state.get("processing_steps", []))
    steps.append("fallback")

    rewritten_query = state.get("rewritten_query", state["query"])
    history = state.get("history", "")
    fallback_reason = state.get("fallback_reason", "")

    from ai.response_generator import generate_fallback_response
    fallback_answer = generate_fallback_response(rewritten_query, history, reason=fallback_reason)

    return {
        "answer": fallback_answer,
        "answered": True,
        "fallback_used": True,
        "matched_files": [],
        "processing_steps": steps,
    }


def hallucination_check_node(state: RAGState) -> dict:
    """
    Verify the generated answer is faithful to retrieved context and its
    citations are real (D3 in SPEC.md). Replaces the old keyword scan,
    which only caught the model admitting "I don't know" -- confident
    fabrication (a wrong course code, an invented prerequisite) sailed
    straight through it undetected.

    Two independent checks:
      a) validate_citations() -- deterministic, no LLM call: every cited
         source must be one of the documents actually retrieved for this
         query. A fabricated citation is itself a form of hallucination.
      b) check_faithfulness() -- structured LLM call: every claim in the
         answer must be supported by the retrieved context.

    citations_missing (matched_files was non-empty but the answer cited
    none of them) does NOT by itself force a fallback. A live 30-query
    RAGAS run showed ~45% of hallucination-triggered fallbacks were
    answers check_faithfulness() had already judged faithful with zero
    unsupported claims -- the model just skipped the prompt's "add a
    Sources line" formatting instruction, which isn't evidence the
    content was wrong. A genuinely fabricated citation (citations_valid
    False) is still real hallucination signal and stays on the same
    footing as unfaithful claims.
    """
    steps = list(state.get("processing_steps", []))
    steps.append("hallucination_check")

    answer = state.get("answer", "")
    reranked_docs = state.get("reranked_docs", [])
    matched_files = state.get("matched_files", [])

    from rag.hallucination_checker import validate_citations, check_faithfulness

    citations_valid, citations_missing = validate_citations(answer, matched_files)
    faithfulness = check_faithfulness(answer, reranked_docs)

    is_hallucinated = (
        not answer
        or not faithfulness["faithful"]
        or not citations_valid
    )

    if citations_missing:
        # Logged for visibility even when it doesn't force a fallback --
        # a rising rate of this still means the generation prompt's
        # citation instruction isn't being followed and is worth revisiting.
        steps.append("missing_citation")

    if is_hallucinated:
        steps.append("hallucination_detected")
        if not answer:
            steps.append("empty_answer")
        if not faithfulness["faithful"]:
            steps.append(f"unfaithful_claims:{len(faithfulness['unsupported_claims'])}")
        if not citations_valid:
            steps.append("invalid_citation")

    result = {
        "hallucination_detected": is_hallucinated,
        "processing_steps": steps,
    }
    if is_hallucinated:
        result["fallback_reason"] = "hallucination_retry"

    return result


# ===== Routing Functions =====

def route_after_safety_and_rewrite(state: RAGState) -> str:
    if state.get("safety_blocked"):
        return END
    if state.get("query_intent") == "NAVIGATION":
        return "fallback"
    return "retrieve"


def route_after_grading(state: RAGState) -> str:
    """
    CRAG now filters reranked_docs in place (grade_documents_node), so an
    empty list already means "nothing survived grading" -- no separate
    docs_relevant flag needed to express the same thing.
    """
    if not state.get("reranked_docs"):
        return "fallback"
    return "generate"


def route_after_hallucination_check(state: RAGState) -> str:
    if state.get("hallucination_detected") and state.get("generation_attempts", 0) <= 1:
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
    graph.add_node("safety_and_rewrite", safety_and_rewrite_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("rerank", rerank_node)
    graph.add_node("grade_documents", grade_documents_node)
    graph.add_node("generate", generate_node)
    graph.add_node("fallback", fallback_node)
    graph.add_node("hallucination_check", hallucination_check_node)

    # Set entry point
    graph.set_entry_point("safety_and_rewrite")

    # Add edges
    graph.add_conditional_edges("safety_and_rewrite", route_after_safety_and_rewrite)
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
        "query_intent": "",
        "documents": [],
        "reranked_docs": [],
        "fallback_reason": "",
        "answer": "",
        "answered": False,
        "matched_files": [],
        "hallucination_detected": False,
        "fallback_used": False,
        "safety_blocked": False,
        "processing_steps": [],
        "generation_attempts": 0,
    }

    result = graph.invoke(initial_state)

    response_time = int((time.time() - start_time) * 1000)

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
            "fallback_used": result.get("fallback_used", False),
            # Previously only inferable by scanning processing_steps for
            # magic strings ("navigation" fired iff "retrieval" is absent,
            # etc.) -- exposing these directly lets evaluation code assert
            # "this query was correctly classified as navigation" or "this
            # fell back for the expected reason" without that guesswork.
            "query_intent": result.get("query_intent", ""),
            "fallback_reason": result.get("fallback_reason", ""),
            "safety_blocked": result.get("safety_blocked", False),
        }
    }
