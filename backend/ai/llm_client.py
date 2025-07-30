# ai/llm_client.py
"""
LLM Client - Manages Google Generative AI connections and configurations
"""

import os
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from typing import Optional

# ========== Google API Configuration ==========
# Use configurable path for Google credentials
from pathlib import Path
_backend_root = Path(__file__).parent.parent
_default_credentials_path = _backend_root / "rag" / "key.json"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", str(_default_credentials_path))
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ========== LLM Client Singletons ==========
_chat_llm_client = None
_embeddings_client = None
_genai_model = None

def get_chat_llm(model: str = "gemini-2.5-flash") -> ChatGoogleGenerativeAI:
    """Get ChatGoogleGenerativeAI client (singleton)"""
    global _chat_llm_client
    if _chat_llm_client is None:
        _chat_llm_client = ChatGoogleGenerativeAI(model=model)
        print(f"[AI] Initialized ChatGoogleGenerativeAI with model: {model}")
    return _chat_llm_client

def get_embeddings_client(model: str = "models/embedding-001") -> GoogleGenerativeAIEmbeddings:
    """Get GoogleGenerativeAIEmbeddings client (singleton)"""
    global _embeddings_client
    if _embeddings_client is None:
        _embeddings_client = GoogleGenerativeAIEmbeddings(model=model)
        print(f"[AI] Initialized GoogleGenerativeAIEmbeddings with model: {model}")
    return _embeddings_client

def get_genai_model(model: str = "gemini-2.5-flash") -> genai.GenerativeModel:
    """Get native Google GenerativeAI model (singleton)"""
    global _genai_model
    if _genai_model is None:
        _genai_model = genai.GenerativeModel(model)
        print(f"[AI] Initialized GenerativeModel with model: {model}")
    return _genai_model

def reset_clients():
    """Reset all client singletons (useful for testing)"""
    global _chat_llm_client, _embeddings_client, _genai_model
    _chat_llm_client = None
    _embeddings_client = None
    _genai_model = None
    print("[AI] Reset all LLM clients")