#!/usr/bin/env python3
"""
Docker RAG Evaluation - 30 query test set
Runs real RAGAS evaluation using Docker container against the backend API
"""

import subprocess
import json
import time
import os
import sys
import requests
from pathlib import Path
from datetime import datetime


def check_backend_running(base_url: str = "http://localhost:5001") -> bool:
    """Check if the backend API is running"""
    try:
        resp = requests.get(f"{base_url}/api/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def run_evaluation_against_api(base_url: str = "http://localhost:5001", sample_size: int = 30):
    """Run real evaluation by querying the backend API"""

    print("=" * 60)
    print("RAG Evaluation - 30 Query Test Set")
    print("=" * 60)

    # Add backend to path for dataset loading
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
    from evaluation.datasets import EvaluationDataset

    # 1. Load dataset
    print("\n[1/4] Loading test dataset...")
    dataset = EvaluationDataset()
    dataset.create_unsw_ground_truth()
    test_data = dataset.generate_test_queries(sample_size=sample_size)
    print(f"  Loaded {len(test_data)} test queries")

    # 2. Query the API
    print(f"\n[2/4] Sending queries to {base_url}...")
    evaluation_data = []
    start_time = time.time()

    for i, query_item in enumerate(test_data, 1):
        query = query_item["query"]
        if i % 5 == 0 or i == 1:
            print(f"  Processing {i}/{len(test_data)}: {query[:40]}...")

        try:
            resp = requests.post(
                f"{base_url}/api/query",
                json={"question": query, "session_id": f"eval_{i}"},
                timeout=60
            )

            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("answer", "")
            else:
                answer = f"API Error: HTTP {resp.status_code}"

        except Exception as e:
            answer = f"Request Error: {str(e)}"

        evaluation_data.append({
            "query": query,
            "generated_answer": answer,
            "retrieved_contexts": [],  # Not available via API
            "ground_truth": query_item.get("ground_truth", ""),
            "category": query_item.get("category"),
            "difficulty": query_item.get("difficulty"),
        })

    gen_time = time.time() - start_time
    print(f"  Completed in {gen_time:.1f}s")

    # 3. Run RAGAS evaluation
    print("\n[3/4] Running RAGAS evaluation...")
    from evaluation.metrics import RAGEvaluator

    evaluator = RAGEvaluator()
    eval_report = evaluator.evaluate_batch(evaluation_data, batch_size=5)

    # 4. Display results
    print("\n[4/4] Results:")
    print("=" * 60)

    aggregate = eval_report.get("aggregate_scores", {})
    summary = eval_report.get("summary", {})

    print(f"Total: {summary.get('total_evaluations', 0)} queries")
    print(f"Success: {summary.get('successful_evaluations', 0)}")
    print(f"Time: {summary.get('total_evaluation_time_seconds', 0):.1f}s")

    print("\nScores:")
    for metric in ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]:
        score = aggregate.get(metric)
        if score is not None:
            level = "Excellent" if score >= 0.85 else "Good" if score >= 0.75 else "Acceptable" if score >= 0.65 else "Needs Work"
            print(f"  {metric.replace('_', ' ').title():25s}: {score:.4f} ({level})")

    # Save results
    eval_dir = Path("data/evaluation")
    eval_dir.mkdir(parents=True, exist_ok=True)
    results_file = eval_dir / f"docker_eval_{int(time.time())}.json"

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "date": datetime.now().isoformat(),
                "queries": len(evaluation_data),
                "type": "docker_api_evaluation",
                "base_url": base_url,
            },
            "aggregate_scores": aggregate,
            "summary": summary,
            "individual_results": eval_report.get("individual_results", []),
        }, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {results_file}")
    print("=" * 60)

    return eval_report


def main():
    """Main entry point"""
    base_url = os.getenv("BACKEND_URL", "http://localhost:5001")

    print("RAG Evaluation - Docker Version")
    print("30 Query Comprehensive Test Set")
    print("=" * 60)

    # Check if backend is running
    if not check_backend_running(base_url):
        print(f"Backend not available at {base_url}")
        print("Please start the backend first: docker-compose up -d")
        print("Or run directly: cd backend && python app.py")
        return 1

    print(f"Backend available at {base_url}")

    try:
        run_evaluation_against_api(base_url=base_url, sample_size=30)
        return 0
    except KeyboardInterrupt:
        print("\nEvaluation interrupted")
        return 1
    except Exception as e:
        print(f"\nEvaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
