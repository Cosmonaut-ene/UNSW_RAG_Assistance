#!/usr/bin/env python3
"""
Standalone evaluation script for RAG system
Can be run independently without the web interface
"""

import sys
import os
import argparse
import json
from pathlib import Path
import time

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from evaluation.pipeline import EvaluationPipeline
from evaluation.datasets import EvaluationDataset
from evaluation.config import QUERY_CATEGORIES


def setup_datasets(sample_size: int = 50):
    """Create evaluation datasets if they don't exist"""
    print("🔧 Setting up evaluation datasets...")
    
    dataset = EvaluationDataset()
    
    # Create ground truth
    print("📝 Creating ground truth dataset...")
    ground_truth = dataset.create_unsw_ground_truth()
    print(f"✅ Created {len(ground_truth)} ground truth items")
    
    # Generate test queries  
    print("❓ Generating test queries...")
    test_queries = dataset.generate_test_queries(sample_size=sample_size)
    print(f"✅ Generated {len(test_queries)} test queries")
    
    # Save datasets
    dataset.save_datasets()
    print("💾 Datasets saved successfully")
    
    return dataset


def run_quick_evaluation(sample_size: int = 10, use_hybrid: bool = True):
    """Run a quick evaluation with a small sample"""
    print(f"🚀 Running quick evaluation (sample_size={sample_size}, hybrid={use_hybrid})...")
    
    pipeline = EvaluationPipeline(use_hybrid_search=use_hybrid)
    
    try:
        results = pipeline.run_comprehensive_evaluation(sample_size=sample_size)
        
        # Print summary
        summary = results.get("summary", {})
        scores = results.get("aggregate_scores", {})
        analysis = results.get("performance_analysis", {})
        
        print("\n" + "="*60)
        print("📊 EVALUATION RESULTS SUMMARY")
        print("="*60)
        
        print(f"Total Evaluations: {summary.get('total_evaluations', 0)}")
        print(f"Successful: {summary.get('successful_evaluations', 0)}")
        print(f"Success Rate: {summary.get('success_rate', 0):.1%}")
        print(f"Total Time: {summary.get('total_evaluation_time_seconds', 0):.1f}s")
        
        print("\n📈 Performance Scores:")
        for metric, score in scores.items():
            if not metric.endswith('_count'):
                print(f"  {metric.replace('_', ' ').title()}: {score:.3f}")
        
        print(f"\n🎯 Overall Performance: {analysis.get('overall_performance', 'Unknown').title()}")
        
        if analysis.get('strengths'):
            print("\n💪 Strengths:")
            for strength in analysis['strengths']:
                print(f"  • {strength}")
        
        if analysis.get('recommendations'):
            print("\n🔧 Recommendations:")
            for rec in analysis['recommendations']:
                print(f"  • {rec}")
        
        print("="*60)
        
        return results
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        return None


def run_category_analysis():
    """Run analysis by query categories"""
    print("🔍 Running category analysis...")
    
    pipeline = EvaluationPipeline()
    
    try:
        results = pipeline.run_category_analysis()
        
        print("\n" + "="*60)
        print("📊 CATEGORY ANALYSIS RESULTS")
        print("="*60)
        
        for category, data in results.get("category_analysis", {}).items():
            print(f"\n📁 {category.replace('_', ' ').title()}:")
            scores = data.get("aggregate_scores", {})
            for metric, score in scores.items():
                if not metric.endswith('_count'):
                    print(f"  {metric.replace('_', ' ').title()}: {score:.3f}")
            
            performance = data.get("performance_analysis", {}).get("overall_performance", "unknown")
            print(f"  Overall: {performance.title()}")
        
        print("="*60)
        
        return results
        
    except Exception as e:
        print(f"❌ Category analysis failed: {e}")
        return None


def run_ab_test():
    """Run A/B test comparing hybrid vs semantic search"""
    print("⚔️ Running A/B test: Hybrid vs Semantic Search...")
    
    pipeline = EvaluationPipeline()
    
    try:
        # Run both tests
        print("🔄 Testing Hybrid Search...")
        hybrid_results = pipeline.run_ab_test(use_hybrid=True)
        
        print("🔄 Testing Semantic Search...")  
        semantic_results = pipeline.run_ab_test(use_hybrid=False)
        
        # Compare results
        comparison = pipeline.generate_performance_comparison(
            semantic_results["test_results"],
            hybrid_results["test_results"]
        )
        
        print("\n" + "="*60)
        print("⚔️ A/B TEST RESULTS: HYBRID VS SEMANTIC")
        print("="*60)
        
        print("🔍 Hybrid Search Results:")
        hybrid_scores = hybrid_results["test_results"].get("aggregate_scores", {})
        for metric, score in hybrid_scores.items():
            if not metric.endswith('_count'):
                print(f"  {metric.replace('_', ' ').title()}: {score:.3f}")
        
        print("\n🎯 Semantic Search Results:")
        semantic_scores = semantic_results["test_results"].get("aggregate_scores", {})
        for metric, score in semantic_scores.items():
            if not metric.endswith('_count'):
                print(f"  {metric.replace('_', ' ').title()}: {score:.3f}")
        
        print("\n📊 Performance Comparison:")
        for metric, comp_data in comparison.get("metrics_comparison", {}).items():
            delta = comp_data.get("delta", 0)
            improvement = "📈" if delta > 0 else "📉" if delta < 0 else "➡️"
            print(f"  {improvement} {metric.replace('_', ' ').title()}: {delta:+.3f} ({comp_data.get('percent_change', 0):+.1f}%)")
        
        print("="*60)
        
        return {
            "hybrid": hybrid_results,
            "semantic": semantic_results, 
            "comparison": comparison
        }
        
    except Exception as e:
        print(f"❌ A/B test failed: {e}")
        return None


def run_single_evaluation(query: str, ground_truth: str = None):
    """Evaluate a single query"""
    print(f"🔍 Evaluating single query: '{query}'")
    
    try:
        from evaluation.metrics import RAGEvaluator
        from services.query_processor import process_with_ai
        from rag.search_engine import search_documents_with_scores
        
        # Generate RAG response
        print("🤖 Generating RAG response...")
        answer, answered, matched_files, performance = process_with_ai(
            query, session_id=f"script_eval_{int(time.time())}"
        )
        
        # Get contexts
        print("🔍 Retrieving contexts...")
        contexts = []
        try:
            similar_docs = search_documents_with_scores(query, k=5)
            contexts = [doc.page_content for doc, score in similar_docs]
        except Exception as e:
            print(f"⚠️ Context retrieval failed: {e}")
            contexts = ["Context retrieval failed"]
        
        # Evaluate with RAGAS
        print("📊 Running RAGAS evaluation...")
        evaluator = RAGEvaluator()
        evaluation_result = evaluator.evaluate_response(
            query=query,
            generated_answer=answer,
            retrieved_contexts=contexts,
            ground_truth_answer=ground_truth
        )
        
        # Display results
        print("\n" + "="*60)
        print("🔍 SINGLE QUERY EVALUATION")
        print("="*60)
        print(f"Query: {query}")
        print(f"Generated Answer: {answer[:200]}{'...' if len(answer) > 200 else ''}")
        print(f"Contexts Retrieved: {len(contexts)}")
        if ground_truth:
            print(f"Ground Truth: {ground_truth[:100]}{'...' if len(ground_truth) > 100 else ''}")
        
        print("\n📊 RAGAS Scores:")
        scores = evaluation_result.get("scores", {})
        for metric, score in scores.items():
            print(f"  {metric.replace('_', ' ').title()}: {score:.3f}")
        
        performance_analysis = evaluation_result.get("performance_analysis", {})
        for metric, level in performance_analysis.items():
            indicator = "🟢" if level in ["excellent", "good"] else "🟡" if level == "acceptable" else "🔴"
            print(f"  {indicator} {metric.replace('_', ' ').title()}: {level.title()}")
        
        print("="*60)
        
        return evaluation_result
        
    except Exception as e:
        print(f"❌ Single evaluation failed: {e}")
        return None


def main():
    """Main evaluation script"""
    parser = argparse.ArgumentParser(description="RAG Evaluation Script")
    parser.add_argument("--mode", choices=["quick", "full", "category", "ab-test", "single"], 
                       default="quick", help="Evaluation mode")
    parser.add_argument("--sample-size", type=int, default=10, 
                       help="Sample size for evaluation (default: 10)")
    parser.add_argument("--no-hybrid", action="store_true", 
                       help="Use semantic search only (disable hybrid)")
    parser.add_argument("--setup-datasets", action="store_true",
                       help="Setup evaluation datasets")
    parser.add_argument("--query", type=str, 
                       help="Single query to evaluate (for single mode)")
    parser.add_argument("--ground-truth", type=str,
                       help="Ground truth answer for single evaluation")
    parser.add_argument("--save-results", action="store_true",
                       help="Save results to file")
    
    args = parser.parse_args()
    
    print("🎯 RAG Evaluation Script")
    print("========================")
    
    # Setup datasets if requested
    if args.setup_datasets:
        setup_datasets(sample_size=args.sample_size * 5)  # Create more for dataset
    
    # Run evaluation based on mode
    results = None
    
    if args.mode == "quick":
        results = run_quick_evaluation(args.sample_size, not args.no_hybrid)
    
    elif args.mode == "full":
        print("🔬 Running comprehensive evaluation...")
        pipeline = EvaluationPipeline(use_hybrid_search=not args.no_hybrid)
        results = pipeline.run_comprehensive_evaluation(sample_size=args.sample_size)
        
        if results:
            # Show detailed results
            print(f"\n✅ Full evaluation completed with {args.sample_size} queries")
            print(f"📊 Check detailed results in evaluation output")
    
    elif args.mode == "category":
        results = run_category_analysis()
    
    elif args.mode == "ab-test":
        results = run_ab_test()
    
    elif args.mode == "single":
        if not args.query:
            print("❌ --query is required for single mode")
            sys.exit(1)
        results = run_single_evaluation(args.query, args.ground_truth)
    
    # Save results if requested
    if args.save_results and results:
        timestamp = int(time.time())
        filename = f"evaluation_results_{args.mode}_{timestamp}.json"
        filepath = backend_dir / "data" / "evaluation" / "results" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Results saved to {filepath}")
    
    print("\n🎉 Evaluation completed!")


if __name__ == "__main__":
    main()