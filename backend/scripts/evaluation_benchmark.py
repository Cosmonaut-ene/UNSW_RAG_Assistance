#!/usr/bin/env python3
"""
Benchmarking script for RAG evaluation system
Compares different configurations and tracks performance over time
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from evaluation.pipeline import EvaluationPipeline
from evaluation.datasets import EvaluationDataset
from evaluation.config import QUERY_CATEGORIES


class EvaluationBenchmark:
    """Benchmark different RAG configurations"""
    
    def __init__(self):
        self.benchmark_results = []
        self.benchmark_start_time = time.time()
    
    def run_configuration_benchmark(self, 
                                  configurations: list,
                                  sample_size: int = 15):
        """
        Benchmark multiple configurations
        
        Args:
            configurations: List of config dicts with keys:
                - name: Configuration name
                - use_hybrid_search: Boolean
                - description: Description
            sample_size: Number of queries per configuration
        """
        
        print(f"🏃 Running configuration benchmark with {len(configurations)} configurations")
        print(f"📊 Sample size: {sample_size} queries per configuration")
        print("="*70)
        
        results = []
        
        for i, config in enumerate(configurations, 1):
            print(f"\n🔧 Configuration {i}/{len(configurations)}: {config['name']}")
            print(f"📝 Description: {config.get('description', 'No description')}")
            
            start_time = time.time()
            
            try:
                # Create pipeline with configuration
                pipeline = EvaluationPipeline(
                    use_hybrid_search=config.get('use_hybrid_search', True)
                )
                
                # Run evaluation
                eval_results = pipeline.run_comprehensive_evaluation(
                    sample_size=sample_size
                )
                
                config_time = time.time() - start_time
                
                # Extract key metrics
                summary = eval_results.get("summary", {})
                scores = eval_results.get("aggregate_scores", {})
                analysis = eval_results.get("performance_analysis", {})
                
                config_result = {
                    "configuration": config,
                    "evaluation_time_seconds": round(config_time, 2),
                    "summary": summary,
                    "scores": scores,
                    "performance_analysis": analysis,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                results.append(config_result)
                
                # Print quick summary
                print(f"⏱️  Time: {config_time:.1f}s")
                print(f"✅ Success rate: {summary.get('success_rate', 0):.1%}")
                print(f"📊 Overall: {analysis.get('overall_performance', 'unknown').title()}")
                
                # Print key scores
                key_metrics = ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]
                for metric in key_metrics:
                    if metric in scores:
                        print(f"   {metric.replace('_', ' ').title()}: {scores[metric]:.3f}")
                
            except Exception as e:
                print(f"❌ Configuration failed: {e}")
                config_result = {
                    "configuration": config,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                results.append(config_result)
        
        self.benchmark_results.extend(results)
        
        # Print comparison summary
        self._print_benchmark_comparison(results)
        
        return results
    
    def run_performance_regression_test(self, 
                                      baseline_results_path: str = None,
                                      sample_size: int = 20):
        """
        Run regression test against baseline performance
        
        Args:
            baseline_results_path: Path to baseline results JSON file
            sample_size: Number of queries to test
        """
        
        print("🔍 Running performance regression test...")
        
        # Load baseline if provided
        baseline_scores = None
        if baseline_results_path and Path(baseline_results_path).exists():
            try:
                with open(baseline_results_path, 'r') as f:
                    baseline_data = json.load(f)
                    if isinstance(baseline_data, list) and baseline_data:
                        baseline_scores = baseline_data[-1].get("aggregate_scores", {})
                    elif isinstance(baseline_data, dict):
                        baseline_scores = baseline_data.get("aggregate_scores", {})
                print(f"📋 Loaded baseline from {baseline_results_path}")
            except Exception as e:
                print(f"⚠️ Could not load baseline: {e}")
        
        # Run current evaluation
        pipeline = EvaluationPipeline(use_hybrid_search=True)
        current_results = pipeline.run_comprehensive_evaluation(sample_size=sample_size)
        current_scores = current_results.get("aggregate_scores", {})
        
        if baseline_scores:
            # Compare with baseline
            comparison = pipeline.generate_performance_comparison(
                {"aggregate_scores": baseline_scores},
                current_results
            )
            
            print("\n" + "="*60)
            print("📊 REGRESSION TEST RESULTS")
            print("="*60)
            
            print("📈 Performance Changes vs Baseline:")
            
            regressions = []
            improvements = []
            
            for metric, comp_data in comparison.get("metrics_comparison", {}).items():
                delta = comp_data.get("delta", 0)
                percent_change = comp_data.get("percent_change", 0)
                
                if delta < -0.05:  # Significant regression (>5% drop)
                    indicator = "🔴"
                    regressions.append(f"{metric}: {delta:.3f} ({percent_change:.1f}%)")
                elif delta > 0.05:  # Significant improvement (>5% gain)
                    indicator = "🟢"
                    improvements.append(f"{metric}: {delta:+.3f} ({percent_change:+.1f}%)")
                else:
                    indicator = "🟡"  # Stable
                
                print(f"  {indicator} {metric.replace('_', ' ').title()}: "
                      f"baseline={comp_data.get('baseline', 0):.3f}, "
                      f"current={comp_data.get('current', 0):.3f}, "
                      f"Δ={delta:+.3f} ({percent_change:+.1f}%)")
            
            # Summary
            if regressions:
                print(f"\n⚠️ {len(regressions)} Performance Regressions Detected:")
                for reg in regressions:
                    print(f"   • {reg}")
            
            if improvements:
                print(f"\n🎉 {len(improvements)} Performance Improvements:")
                for imp in improvements:
                    print(f"   • {imp}")
            
            if not regressions and not improvements:
                print("\n✅ Performance is stable compared to baseline")
            
            print("="*60)
        
        else:
            print("\n📊 Current Performance (no baseline for comparison):")
            for metric, score in current_scores.items():
                if not metric.endswith('_count'):
                    print(f"  {metric.replace('_', ' ').title()}: {score:.3f}")
        
        return {
            "current_results": current_results,
            "baseline_scores": baseline_scores,
            "comparison": comparison if baseline_scores else None
        }
    
    def run_category_performance_benchmark(self):
        """Benchmark performance across different query categories"""
        
        print("📁 Running category performance benchmark...")
        
        pipeline = EvaluationPipeline()
        category_results = {}
        
        for category in QUERY_CATEGORIES[:5]:  # Test top 5 categories
            print(f"📂 Testing category: {category}")
            
            try:
                results = pipeline.run_comprehensive_evaluation(
                    sample_size=8,  # Smaller sample per category
                    categories=[category]
                )
                
                category_results[category] = {
                    "scores": results.get("aggregate_scores", {}),
                    "performance": results.get("performance_analysis", {}),
                    "summary": results.get("summary", {})
                }
                
            except Exception as e:
                print(f"❌ Category {category} failed: {e}")
                category_results[category] = {"error": str(e)}
        
        # Print category comparison
        print("\n" + "="*60)
        print("📁 CATEGORY PERFORMANCE BENCHMARK")
        print("="*60)
        
        for category, data in category_results.items():
            if "error" not in data:
                scores = data.get("scores", {})
                performance = data.get("performance", {}).get("overall_performance", "unknown")
                
                print(f"\n📂 {category.replace('_', ' ').title()}:")
                print(f"   Overall: {performance.title()}")
                
                for metric in ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]:
                    if metric in scores:
                        print(f"   {metric.replace('_', ' ').title()}: {scores[metric]:.3f}")
            else:
                print(f"\n📂 {category.replace('_', ' ').title()}: ❌ {data['error']}")
        
        print("="*60)
        
        return category_results
    
    def _print_benchmark_comparison(self, results: list):
        """Print comparison table for benchmark results"""
        
        if len(results) < 2:
            return
        
        print("\n" + "="*80)
        print("📊 CONFIGURATION BENCHMARK COMPARISON")
        print("="*80)
        
        # Header
        print(f"{'Configuration':<20} {'Overall':<12} {'Faithfulness':<12} {'Relevancy':<12} {'Recall':<12} {'Precision':<12}")
        print("-" * 80)
        
        # Results
        for result in results:
            if "error" not in result:
                config_name = result["configuration"]["name"][:18]
                performance = result["performance_analysis"].get("overall_performance", "unknown")[:10]
                scores = result["scores"]
                
                faithfulness = scores.get("faithfulness", 0)
                relevancy = scores.get("answer_relevancy", 0)
                recall = scores.get("context_recall", 0)
                precision = scores.get("context_precision", 0)
                
                print(f"{config_name:<20} {performance.title():<12} {faithfulness:<12.3f} {relevancy:<12.3f} {recall:<12.3f} {precision:<12.3f}")
            else:
                config_name = result["configuration"]["name"][:18]
                print(f"{config_name:<20} {'ERROR':<12} {'-':<12} {'-':<12} {'-':<12} {'-':<12}")
        
        print("="*80)
        
        # Find best configuration
        best_config = None
        best_score = -1
        
        for result in results:
            if "error" not in result:
                scores = result["scores"]
                # Calculate average of main metrics
                avg_score = sum([
                    scores.get("faithfulness", 0),
                    scores.get("answer_relevancy", 0),
                    scores.get("context_recall", 0),
                    scores.get("context_precision", 0)
                ]) / 4
                
                if avg_score > best_score:
                    best_score = avg_score
                    best_config = result["configuration"]["name"]
        
        if best_config:
            print(f"🏆 Best Configuration: {best_config} (avg score: {best_score:.3f})")
    
    def save_benchmark_results(self, filepath: str = None):
        """Save benchmark results to file"""
        
        if not filepath:
            timestamp = int(time.time())
            filepath = f"benchmark_results_{timestamp}.json"
        
        benchmark_data = {
            "benchmark_metadata": {
                "total_time_seconds": round(time.time() - self.benchmark_start_time, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "total_configurations": len(self.benchmark_results)
            },
            "results": self.benchmark_results
        }
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(benchmark_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Benchmark results saved to {filepath}")
        return str(filepath)


def main():
    """Main benchmarking script"""
    print("🏁 RAG Evaluation Benchmark Suite")
    print("==================================")
    
    benchmark = EvaluationBenchmark()
    
    # Define configurations to test
    configurations = [
        {
            "name": "hybrid_search",
            "use_hybrid_search": True,
            "description": "Hybrid semantic + BM25 search"
        },
        {
            "name": "semantic_only", 
            "use_hybrid_search": False,
            "description": "Pure semantic search with ChromaDB"
        }
    ]
    
    try:
        # Run configuration benchmark
        print("1️⃣ Running configuration benchmark...")
        benchmark.run_configuration_benchmark(configurations, sample_size=12)
        
        # Run category benchmark
        print("\n2️⃣ Running category performance benchmark...")
        benchmark.run_category_performance_benchmark()
        
        # Run regression test if baseline exists
        baseline_path = backend_dir / "data" / "evaluation" / "baseline_results.json"
        if baseline_path.exists():
            print("\n3️⃣ Running regression test...")
            benchmark.run_performance_regression_test(str(baseline_path))
        else:
            print("\n3️⃣ No baseline found, skipping regression test")
            print(f"💡 To enable regression tests, save baseline results to: {baseline_path}")
        
        # Save results
        results_path = benchmark.save_benchmark_results(
            str(backend_dir / "data" / "evaluation" / "results" / f"benchmark_{int(time.time())}.json")
        )
        
        print(f"\n🎉 Benchmark completed!")
        print(f"📊 Results saved to: {results_path}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Benchmark interrupted by user")
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()