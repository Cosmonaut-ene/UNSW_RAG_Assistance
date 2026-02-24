"""
RAG Evaluation Module for UNSW CSE Chatbot
Provides comprehensive evaluation metrics for RAG system performance
"""

from .metrics import RAGEvaluator
from .datasets import EvaluationDataset
from .pipeline import EvaluationPipeline

__all__ = ['RAGEvaluator', 'EvaluationDataset', 'EvaluationPipeline']