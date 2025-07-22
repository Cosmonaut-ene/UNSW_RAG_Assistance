# rag/__init__.py
from rag.gemini3 import build_rag_qa_chain, ask_with_rag_and_fallback, ask_with_hybrid_search

qa_chain = None

def init_rag_chain():
    global qa_chain
    if qa_chain is None:
        print("[RAG] Initializing Gemini3 RAG QA Chain...")
        qa_chain = build_rag_qa_chain()

def process_with_rag(question: str) -> str:
    global qa_chain
    if qa_chain is None:
        init_rag_chain()
    result = qa_chain({"query": question})
    return result["result"]

def process_with_rag_detailed(question: str, conversation_history: list = None) -> dict:
    """
    Process question with hybrid search (RAG + keyword) and return detailed results
    """
    global qa_chain
    if qa_chain is None:
        init_rag_chain()
    return ask_with_hybrid_search(question, qa_chain, conversation_history)

def process_with_rag_only(question: str) -> dict:
    """
    Process question with RAG only (original method)
    """
    global qa_chain
    if qa_chain is None:
        init_rag_chain()
    return ask_with_rag_and_fallback(question, qa_chain)
