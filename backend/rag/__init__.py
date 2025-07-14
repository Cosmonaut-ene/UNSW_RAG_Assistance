# rag/__init__.py
from rag.gemini3 import build_rag_qa_chain, ask_with_rag_and_fallback

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

def process_with_rag_detailed(question: str) -> dict:
    """
    Process question with RAG and return detailed results including matched files
    """
    global qa_chain
    if qa_chain is None:
        init_rag_chain()
    return ask_with_rag_and_fallback(question, qa_chain)
