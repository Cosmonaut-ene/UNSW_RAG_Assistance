#!/usr/bin/env python3
"""
RAG Evaluation System - Real RAGAS evaluation
Evaluates the UNSW CSE chatbot RAG system using actual pipeline + RAGAS metrics
"""

import json
import sys
import os
import time
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))


def run_real_evaluation(sample_size: int = None):
    """Run real RAGAS evaluation against the live RAG pipeline"""

    print("=" * 70)
    print("RAG Evaluation System - Real RAGAS Evaluation")
    print("=" * 70)
    print()

    # 1. Load test dataset
    print("[1/5] Loading evaluation dataset...")
    from evaluation.datasets import EvaluationDataset

    dataset = EvaluationDataset()
    dataset.create_unsw_ground_truth()
    test_data = dataset.generate_test_queries(sample_size=sample_size or 50)
    print(f"  Loaded {len(test_data)} test queries")

    # Show distribution
    category_counts = {}
    for q in test_data:
        cat = q.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    print("  Category distribution:")
    for cat, count in sorted(category_counts.items()):
        print(f"    {cat}: {count}")

    # 2. Generate RAG responses for each query
    print(f"\n[2/5] Generating RAG responses for {len(test_data)} queries...")
    from services.query_processor import process_with_ai
    from rag.vector_store import load_vector_store
    from rag.hybrid_search import HybridSearchEngine
    from rag.search_engine import search_documents_with_scores

    evaluation_data = []
    start_time = time.time()

    for i, query_item in enumerate(test_data, 1):
        query = query_item["query"]
        if i % 10 == 0 or i == 1:
            elapsed = time.time() - start_time
            print(f"  Processing {i}/{len(test_data)}: {query[:50]}... ({elapsed:.1f}s elapsed)")

        try:
            # Get RAG response
            answer, answered, matched_files, performance = process_with_ai(
                query, session_id=f"eval_{i}_{int(time.time())}"
            )

            # Get retrieved contexts
            contexts = []
            try:
                results = search_documents_with_scores(query, k=10)
                contexts = [doc.page_content for doc, score in results if hasattr(doc, 'page_content')]
            except Exception as e:
                print(f"  Warning: context retrieval failed for query {i}: {e}")

            # Remove duplicates and empties
            contexts = list(set(c for c in contexts if c and c.strip()))

            evaluation_data.append({
                "query": query,
                "generated_answer": answer or "",
                "retrieved_contexts": contexts[:10],
                "ground_truth": query_item.get("ground_truth", ""),
                "category": query_item.get("category"),
                "difficulty": query_item.get("difficulty"),
                "answered": answered,
                "response_time_ms": performance.get("response_time_ms", 0) if performance else 0,
            })

        except Exception as e:
            print(f"  ERROR on query {i}: {e}")
            evaluation_data.append({
                "query": query,
                "generated_answer": f"Error: {str(e)}",
                "retrieved_contexts": [],
                "ground_truth": query_item.get("ground_truth", ""),
                "category": query_item.get("category"),
                "difficulty": query_item.get("difficulty"),
                "error": str(e),
            })

    gen_time = time.time() - start_time
    print(f"  Response generation completed in {gen_time:.1f}s")

    # 3. Run RAGAS evaluation
    print("\n[3/5] Running RAGAS evaluation...")
    from evaluation.metrics import RAGEvaluator

    evaluator = RAGEvaluator()
    eval_report = evaluator.evaluate_batch(evaluation_data, batch_size=5)

    # 4. Analyze results
    print("\n[4/5] Analyzing results...")
    print("\n" + "=" * 70)
    print("RAGAS Evaluation Results")
    print("=" * 70)

    aggregate = eval_report.get("aggregate_scores", {})
    summary = eval_report.get("summary", {})

    print(f"\nTotal queries evaluated: {summary.get('total_evaluations', 0)}")
    print(f"Successful evaluations: {summary.get('successful_evaluations', 0)}")
    print(f"Failed evaluations: {summary.get('failed_evaluations', 0)}")
    print(f"Total evaluation time: {summary.get('total_evaluation_time_seconds', 0):.1f}s")

    print("\nAggregate Scores:")
    metrics = ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]
    for metric in metrics:
        score = aggregate.get(metric, None)
        if score is not None:
            level = "Excellent" if score >= 0.85 else "Good" if score >= 0.75 else "Acceptable" if score >= 0.65 else "Needs Improvement"
            print(f"  {metric.replace('_', ' ').title():25s}: {score:.4f} ({level})")

    # Overall average
    metric_scores = [aggregate.get(m, 0) for m in metrics if m in aggregate]
    if metric_scores:
        overall_avg = sum(metric_scores) / len(metric_scores)
        print(f"\n  {'Overall Average':25s}: {overall_avg:.4f}")

    # Category breakdown
    print("\nCategory Breakdown:")
    category_results = {}
    for result in eval_report.get("individual_results", []):
        cat = None
        # Find category from evaluation_data
        for ed in evaluation_data:
            if ed["query"] == result.get("query"):
                cat = ed.get("category")
                break
        if cat and result.get("scores"):
            if cat not in category_results:
                category_results[cat] = []
            scores = result["scores"]
            avg = sum(scores.values()) / len(scores) if scores else 0
            category_results[cat].append(avg)

    for cat, scores in sorted(category_results.items()):
        avg = sum(scores) / len(scores)
        print(f"  {cat.replace('_', ' ').title():30s}: {avg:.4f} ({len(scores)} queries)")

    # 5. Save results
    print("\n[5/5] Saving results...")
    eval_dir = Path("data/evaluation")
    eval_dir.mkdir(parents=True, exist_ok=True)

    results_file = eval_dir / f"real_evaluation_{int(time.time())}.json"
    full_results = {
        "metadata": {
            "evaluation_date": datetime.now().isoformat(),
            "total_queries": len(evaluation_data),
            "generation_time_seconds": round(gen_time, 2),
            "version": "2.0",
            "type": "real_ragas_evaluation"
        },
        "aggregate_scores": aggregate,
        "summary": summary,
        "performance_analysis": eval_report.get("performance_analysis", {}),
        "individual_results": eval_report.get("individual_results", []),
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(full_results, f, indent=2, ensure_ascii=False)
    print(f"  Results saved to: {results_file}")

    print("\n" + "=" * 70)
    print("Evaluation complete!")
    print("=" * 70)

    return eval_report


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="RAG Evaluation System")
    parser.add_argument("--sample-size", type=int, default=50,
                        help="Number of queries to evaluate (default: 50)")
    args = parser.parse_args()

    try:
        run_real_evaluation(sample_size=args.sample_size)
        return 0
    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user")
        return 1
    except Exception as e:
        print(f"\nEvaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
