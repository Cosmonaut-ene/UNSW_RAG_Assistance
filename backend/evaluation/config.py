"""
Configuration for RAG evaluation system
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
EVALUATION_DIR = BASE_DIR / "evaluation"
DATA_DIR = BASE_DIR.parent / "data" / "evaluation"
RESULTS_DIR = DATA_DIR / "results"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Evaluation dataset paths
GROUND_TRUTH_PATH = DATA_DIR / "ground_truth.json"
TEST_QUERIES_PATH = DATA_DIR / "test_queries.json"
EVALUATION_RESULTS_PATH = RESULTS_DIR / "evaluation_results.json"

# RAGAS Configuration
RAGAS_CONFIG = {
    "metrics": [
        "faithfulness",
        "answer_relevancy", 
        "context_recall",
        "context_precision"
    ],
    "llm_temperature": 0.0,  # Consistent evaluation
    "batch_size": 10,
    "timeout": 120
}

# Test configuration
TEST_CONFIG = {
    "sample_size": 50,  # Number of queries to test
    "random_seed": 42,
    "include_conversation_history": True,
    "evaluate_hybrid_search": True
}

# Performance thresholds for evaluation
PERFORMANCE_THRESHOLDS = {
    "faithfulness": {
        "excellent": 0.9,
        "good": 0.8,
        "acceptable": 0.7,
        "poor": 0.6
    },
    "answer_relevancy": {
        "excellent": 0.9,
        "good": 0.8,
        "acceptable": 0.7,
        "poor": 0.6
    },
    "context_recall": {
        "excellent": 0.9,
        "good": 0.8,
        "acceptable": 0.7,
        "poor": 0.6
    },
    "context_precision": {
        "excellent": 0.9,
        "good": 0.8,
        "acceptable": 0.7,
        "poor": 0.6
    }
}

# Query categories for evaluation
QUERY_CATEGORIES = [
    "course_information",
    "prerequisites", 
    "degree_programs",
    "campus_facilities",
    "admission_requirements",
    "general_inquiries",
    "conversation_followup"
]