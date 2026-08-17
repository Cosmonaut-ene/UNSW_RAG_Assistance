# ai/llm_client.py
"""
LLM Client - Manages Google Generative AI connections and configurations.
Embeddings use a local sentence-transformers model (no API quota limits).
"""

import os
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from typing import Optional

# ========== Google API Configuration ==========
from pathlib import Path
_backend_root = Path(__file__).parent.parent
_default_credentials_path = _backend_root / "config" / "key.json"

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", str(_default_credentials_path))
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ========== LLM Client Singletons ==========
_chat_llm_client = None
_embeddings_client = None
_genai_models: dict = {}  # keyed by model name -- see get_genai_model()

# Local embedding model — no API key, no rate limits
# all-MiniLM-L6-v2: 384-dim, ~22MB, fast on CPU, good retrieval quality
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

def get_chat_llm(model: str = "gemini-2.5-flash") -> ChatGoogleGenerativeAI:
    """Get ChatGoogleGenerativeAI client (singleton)"""
    global _chat_llm_client
    if _chat_llm_client is None:
        _chat_llm_client = ChatGoogleGenerativeAI(model=model)
        print(f"[AI] Initialized ChatGoogleGenerativeAI with model: {model}")
    return _chat_llm_client

def get_embeddings_client(model: str = None) -> HuggingFaceEmbeddings:
    """
    Get local HuggingFace embeddings client (singleton).
    Uses sentence-transformers/all-MiniLM-L6-v2 — no API quota limits.
    """
    global _embeddings_client
    if _embeddings_client is None:
        model_name = model or EMBEDDING_MODEL_NAME
        _embeddings_client = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        print(f"[AI] Initialized local HuggingFaceEmbeddings with model: {model_name}")
    return _embeddings_client

def get_genai_model(model: str = "gemini-2.5-flash") -> genai.GenerativeModel:
    """
    Get native Google GenerativeAI model (singleton per model name).

    Previously cached in a single module-level variable regardless of the
    `model` argument, so whichever model name was requested first silently
    won for the rest of the process -- callers asking for a different model
    later got the first one back with no error. Caching by name is what
    lets different call sites (e.g. a lighter model for simple classification
    tasks vs. the model used for generation) actually take effect.
    """
    if model not in _genai_models:
        _genai_models[model] = genai.GenerativeModel(model)
        print(f"[AI] Initialized GenerativeModel with model: {model}")
    return _genai_models[model]

def reset_clients():
    """Reset all client singletons (useful for testing)"""
    global _chat_llm_client, _embeddings_client, _genai_models
    _chat_llm_client = None
    _embeddings_client = None
    _genai_models = {}
    print("[AI] Reset all LLM clients")