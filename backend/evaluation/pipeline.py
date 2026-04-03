"""
Automated evaluation pipeline that integrates with existing RAG system
"""

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from .metrics import RAGEvaluator
from .datasets import EvaluationDataset
from .config import TEST_CONFIG

# Import existing RAG system components
from services.query_processor import process_with_ai


class EvaluationPipeline:
    """Automated pipeline for evaluating RAG system performance"""
    
    def __init__(self, use_hybrid_search: bool = True):
        self.evaluator = RAGEvaluator()
        self.dataset = EvaluationDataset()
        self.use_hybrid_search = use_hybrid_search
        self.evaluation_results = []
        
    def run_comprehensive_evaluation(self, 
                                   sample_size: int = None,
                                   categories: List[str] = None) -> Dict[str, Any]:
        """
        Run comprehensive evaluation of the RAG system
        
        Args:
            sample_size: Number of test queries to evaluate
            categories: Specific categories to test (if None, tests all)
            
        Returns:
            Comprehensive evaluation report
        """
        
        print("🔍 Starting comprehensive RAG evaluation...")
        start_time = time.time()
        
        # Load or create test dataset
        self.dataset.load_datasets()
        if not self.dataset.test_queries:
            print("Creating test dataset...")
            self.dataset.create_unsw_ground_truth()
            self.dataset.generate_test_queries(sample_size or TEST_CONFIG["sample_size"])
            self.dataset.save_datasets()
        
        # Filter queries by category if specified
        test_queries = self.dataset.test_queries
        if categories:
            test_queries = [q for q in test_queries if q.get('category') in categories]
        
        # Limit sample size if specified
        if sample_size:
            test_queries = test_queries[:sample_size]
        
        print(f"Evaluating {len(test_queries)} test queries...")
        
        # Generate RAG responses for each test query
        evaluation_data = []
        
        for i, query_item in enumerate(test_queries):
            print(f"Processing query {i+1}/{len(test_queries)}: {query_item['query'][:50]}...")
            
            try:
                # Generate response using existing RAG system
                rag_response = self._generate_rag_response(query_item['query'])
                
                evaluation_data.append({
                    "query": query_item['query'],
                    "generated_answer": rag_response['answer'],
                    "retrieved_contexts": rag_response['contexts'],
                    "ground_truth": query_item.get('ground_truth', query_item.get('expected_answer', query_item.get('ground_truth_answer'))),
                    "query_metadata": {
                        "category": query_item.get('category'),
                        "difficulty": query_item.get('difficulty'),
                        "query_type": query_item.get('query_type'),
                        "expected_keywords": query_item.get('expected_context_keywords', [])
                    },
                    "rag_metadata": rag_response['metadata']
                })
                
            except Exception as e:
                print(f"Error processing query {i+1}: {e}")
                evaluation_data.append({
                    "query": query_item['query'],
                    "generated_answer": "Error generating response",
                    "retrieved_contexts": [],
                    "ground_truth": query_item.get('ground_truth', query_item.get('expected_answer', query_item.get('ground_truth_answer'))),
                    "error": str(e)
                })
        
        # Run RAGAS evaluation
        print("Running RAGAS evaluation...")
        evaluation_report = self.evaluator.evaluate_batch(evaluation_data)
        
        # Add pipeline metadata
        evaluation_report["pipeline_metadata"] = {
            "total_pipeline_time_seconds": round(time.time() - start_time, 3),
            "test_config": TEST_CONFIG,
            "use_hybrid_search": self.use_hybrid_search,
            "categories_tested": categories or "all",
            "sample_size_requested": sample_size,
            "actual_queries_tested": len(test_queries)
        }
        
        # Store results
        self.evaluation_results.append(evaluation_report)
        
        print(f"✅ Evaluation completed in {time.time() - start_time:.1f} seconds")
        return evaluation_report
    
    def _generate_rag_response(self, query: str) -> Dict[str, Any]:
        """
        Generate RAG response using existing system
        
        Returns:
            Dictionary with answer, contexts, and metadata
        """
        
        try:
            # Use existing query processor to generate response
            answer, answered, matched_files, performance = process_with_ai(
                query, 
                session_id=f"eval_{int(time.time())}"
            )
            
            # Use the actual contexts that were passed to the LLM during generation.
            # These come directly from the LangGraph pipeline (post-rerank, post-CRAG),
            # ensuring RAGAS evaluates faithfulness against the real retrieved context.
            contexts = [ctx for ctx in performance.get("retrieved_contexts", []) if ctx and ctx.strip()]
            
            return {
                "answer": answer,
                "contexts": contexts[:10],  # Limit to top 10 contexts
                "metadata": {
                    "answered": answered,
                    "matched_files": matched_files,
                    "performance": performance,
                    "context_count": len(contexts)
                }
            }
            
        except Exception as e:
            print(f"Error generating RAG response: {e}")
            return {
                "answer": f"Error: {str(e)}",
                "contexts": [],
                "metadata": {"error": str(e)}
            }
    
    def run_category_analysis(self) -> Dict[str, Any]:
        """Run evaluation analysis by query categories"""
        
        print("🔍 Running category-based evaluation analysis...")
        
        from .config import QUERY_CATEGORIES
        
        category_results = {}
        
        for category in QUERY_CATEGORIES:
            print(f"Evaluating category: {category}")
            
            category_report = self.run_comprehensive_evaluation(
                sample_size=10,  # Smaller sample per category
                categories=[category]
            )
            
            category_results[category] = {
                "aggregate_scores": category_report["aggregate_scores"],
                "performance_analysis": category_report["performance_analysis"],
                "summary": category_report["summary"]
            }
        
        return {
            "category_analysis": category_results,
            "timestamp": datetime.now().isoformat(),
            "analysis_type": "by_category"
        }
    
    def run_difficulty_analysis(self) -> Dict[str, Any]:
        """Run evaluation analysis by query difficulty levels"""
        
        print("🔍 Running difficulty-based evaluation analysis...")
        
        difficulty_levels = ["easy", "medium", "hard"]
        difficulty_results = {}
        
        for difficulty in difficulty_levels:
            print(f"Evaluating difficulty: {difficulty}")
            
            # Get queries of this difficulty
            difficulty_queries = self.dataset.get_queries_by_difficulty(difficulty)
            
            if difficulty_queries:
                # Generate evaluation data
                evaluation_data = []
                for query_item in difficulty_queries[:10]:  # Limit sample
                    try:
                        rag_response = self._generate_rag_response(query_item['query'])
                        evaluation_data.append({
                            "query": query_item['query'],
                            "generated_answer": rag_response['answer'],
                            "retrieved_contexts": rag_response['contexts'],
                            "ground_truth": query_item.get('ground_truth', query_item.get('expected_answer', query_item.get('ground_truth_answer')))
                        })
                    except Exception as e:
                        print(f"Error in difficulty analysis: {e}")
                        continue
                
                if evaluation_data:
                    difficulty_report = self.evaluator.evaluate_batch(evaluation_data)
                    difficulty_results[difficulty] = {
                        "aggregate_scores": difficulty_report["aggregate_scores"],
                        "performance_analysis": difficulty_report["performance_analysis"],
                        "summary": difficulty_report["summary"]
                    }
        
        return {
            "difficulty_analysis": difficulty_results,
            "timestamp": datetime.now().isoformat(),
            "analysis_type": "by_difficulty"
        }
    
    def run_ab_test(self, use_hybrid: bool = True) -> Dict[str, Any]:
        """
        Run A/B test comparing hybrid search vs pure semantic search
        
        Args:
            use_hybrid: Whether to test hybrid search (True) or pure semantic (False)
        """
        
        print(f"🔍 Running A/B test: {'Hybrid' if use_hybrid else 'Semantic'} search...")
        
        # Set search mode
        original_mode = self.use_hybrid_search
        self.use_hybrid_search = use_hybrid
        
        try:
            # Run evaluation with current search mode
            test_results = self.run_comprehensive_evaluation(sample_size=20)
            
            return {
                "search_mode": "hybrid" if use_hybrid else "semantic",
                "test_results": test_results,
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            # Restore original mode
            self.use_hybrid_search = original_mode
    
    def generate_performance_comparison(self, 
                                      baseline_results: Dict,
                                      current_results: Dict) -> Dict[str, Any]:
        """Compare performance between two evaluation runs"""
        
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "comparison_type": "performance_delta",
            "metrics_comparison": {}
        }
        
        baseline_scores = baseline_results.get("aggregate_scores", {})
        current_scores = current_results.get("aggregate_scores", {})
        
        for metric in baseline_scores:
            if metric in current_scores and not metric.endswith('_count'):
                baseline_val = baseline_scores[metric]
                current_val = current_scores[metric]
                delta = current_val - baseline_val
                percent_change = (delta / baseline_val * 100) if baseline_val != 0 else 0
                
                comparison["metrics_comparison"][metric] = {
                    "baseline": baseline_val,
                    "current": current_val,
                    "delta": round(delta, 4),
                    "percent_change": round(percent_change, 2),
                    "improvement": delta > 0
                }
        
        return comparison
    
    def save_pipeline_results(self, filepath: str = None):
        """Save all pipeline evaluation results"""
        
        if not filepath:
            filepath = f"data/evaluation/results/pipeline_results_{int(time.time())}.json"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.evaluation_results, f, indent=2, ensure_ascii=False)
            print(f"Pipeline results saved to {filepath}")
        except Exception as e:
            print(f"Error saving pipeline results: {e}")
    
    def get_latest_results(self) -> Optional[Dict[str, Any]]:
        """Get the most recent evaluation results"""
        return self.evaluation_results[-1] if self.evaluation_results else None