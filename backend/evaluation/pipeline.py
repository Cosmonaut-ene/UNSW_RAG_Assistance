"""
Automated evaluation pipeline that integrates with existing RAG system
"""

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from .metrics import RAGEvaluator
from .datasets import EvaluationDataset
from .config import TEST_CONFIG, RESULTS_DIR

# Import existing RAG system components
from services.query_processor import process_with_ai


class EvaluationPipeline:
    """Automated pipeline for evaluating RAG system performance"""

    def __init__(self, use_hybrid_search: bool = True, retrieval_config=None):
        self.evaluator = RAGEvaluator()
        self.dataset = EvaluationDataset()
        self.use_hybrid_search = use_hybrid_search
        self.retrieval_config = retrieval_config  # Optional RetrievalConfig for tuning
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
        
        # Load or create test dataset. A cached test_queries.json smaller
        # than what this run actually asked for must not be reused as-is --
        # now that evaluation/ data persists across runs (see
        # _save_run_report()), a leftover file from an earlier small sample_size
        # run would otherwise silently truncate every later, larger request
        # down to whatever was cached, with no error or warning.
        requested_size = sample_size or TEST_CONFIG["sample_size"]
        self.dataset.load_datasets()
        if not self.dataset.test_queries or len(self.dataset.test_queries) < requested_size:
            print("Creating test dataset...")
            self.dataset.create_unsw_ground_truth()
            self.dataset.generate_test_queries(requested_size)
            self.dataset.save_datasets()
        
        # Filter queries by category if specified. No further sample_size
        # slicing here -- self.dataset.generate_test_queries() already
        # applied sample_size to the RAGAS-scored portion above; behavioral
        # items (expected_behavior set, see EvaluationDataset) are appended
        # after that and must survive intact, or a blanket test_queries[:N]
        # here would silently drop the navigation/out-of-scope checks
        # whenever the scored portion alone reached sample_size.
        all_queries = self.dataset.test_queries
        if categories:
            all_queries = [q for q in all_queries if q.get('category') in categories]

        scored_queries = [q for q in all_queries if 'expected_behavior' not in q]
        behavioral_queries = [q for q in all_queries if 'expected_behavior' in q]

        print(f"Evaluating {len(scored_queries)} scored queries + {len(behavioral_queries)} behavioral queries...")

        # Generate RAG responses for each RAGAS-scored test query
        evaluation_data = []

        for i, query_item in enumerate(scored_queries):
            print(f"Processing query {i+1}/{len(scored_queries)}: {query_item['query'][:50]}...")

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

        # Behavioral checks (navigation intent, out-of-scope fallback) --
        # these have no ground_truth for RAGAS to score against (there's no
        # "correct grounded answer" for a query the corpus doesn't cover),
        # so they're checked directly against rag_metadata.performance
        # instead and reported separately.
        behavioral_test_results = self._run_behavioral_checks(behavioral_queries)

        # Add pipeline metadata
        evaluation_report["pipeline_metadata"] = {
            "total_pipeline_time_seconds": round(time.time() - start_time, 3),
            "test_config": TEST_CONFIG,
            "use_hybrid_search": self.use_hybrid_search,
            "categories_tested": categories or "all",
            "sample_size_requested": sample_size,
            "actual_queries_tested": len(scored_queries) + len(behavioral_queries)
        }
        evaluation_report["behavioral_test_results"] = behavioral_test_results

        # Store results
        self.evaluation_results.append(evaluation_report)
        self._save_run_report(evaluation_report)

        print(f"✅ Evaluation completed in {time.time() - start_time:.1f} seconds")
        return evaluation_report

    def _run_behavioral_checks(self, behavioral_queries: List[Dict]) -> Dict[str, Any]:
        """
        Run each behavioral query through the real pipeline and check its
        actual performance metadata against what the query was designed to
        prove:
          - expected_behavior="navigation": query_intent must be
            "NAVIGATION" (safety_and_rewrite_node correctly detected it and
            routed straight to fallback_node without attempting retrieval).
          - expected_behavior="fallback": fallback_used OR safety_blocked
            must be True -- the pipeline must decline rather than fabricate
            an answer to a query the knowledge base has no source document
            for, whether that's via CRAG/hallucination_check's fallback
            path or safety_check classifying it OFF_TOPIC outright (a live
            smoke test showed "What's the weather forecast?" correctly
            rejected as OFF_TOPIC, which never sets fallback_used -- that's
            a different but equally valid form of "didn't hallucinate").

        Returns a summary + per-query pass/fail list, not a RAGAS score --
        there's no meaningful "faithfulness" to measure when the correct
        answer is "the system shouldn't answer this from context".
        """
        results = []
        for query_item in behavioral_queries:
            query = query_item['query']
            expected = query_item.get('expected_behavior')
            try:
                rag_response = self._generate_rag_response(query)
                performance = rag_response['metadata'].get('performance', {})

                if expected == 'navigation':
                    passed = performance.get('query_intent') == 'NAVIGATION'
                elif expected == 'fallback':
                    passed = performance.get('fallback_used', False) or performance.get('safety_blocked', False)
                else:
                    passed = None  # unknown expected_behavior -- not a failure, just unscoreable

                results.append({
                    "query": query,
                    "category": query_item.get('category'),
                    "expected_behavior": expected,
                    "passed": passed,
                    "query_intent": performance.get('query_intent'),
                    "fallback_used": performance.get('fallback_used'),
                    "fallback_reason": performance.get('fallback_reason'),
                    "safety_blocked": performance.get('safety_blocked'),
                })
            except Exception as e:
                print(f"Error running behavioral check for '{query}': {e}")
                results.append({
                    "query": query,
                    "category": query_item.get('category'),
                    "expected_behavior": expected,
                    "passed": False,
                    "error": str(e),
                })

        scoreable = [r for r in results if r["passed"] is not None]
        passed_count = sum(1 for r in scoreable if r["passed"])

        return {
            "total_count": len(results),
            "passed_count": passed_count,
            "pass_rate": round(passed_count / len(scoreable), 4) if scoreable else None,
            "results": results,
        }

    def _save_run_report(self, evaluation_report: Dict[str, Any]) -> None:
        """
        Persist the full report -- every query's input (query, ground_truth),
        output (generated_answer), and intermediate process (retrieved_contexts,
        rag_metadata.performance.processing_steps, fallback reason, RAGAS
        scores) -- to a timestamped file, one per run.

        A `docker compose run --rm` container throws all of this away the
        moment it exits; a 30-query RAGAS run takes ~30+ minutes, and without
        this, post-hoc analysis (e.g. "why did fallback_rate not drop as much
        as expected") means re-running the whole evaluation just to get data
        that already existed in memory the first time.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = RESULTS_DIR / f"eval_run_{timestamp}.json"
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(evaluation_report, f, indent=2, ensure_ascii=False, default=str)
            print(f"[EvaluationPipeline] Full run report saved to {filepath}")
        except Exception as e:
            print(f"[EvaluationPipeline] Failed to save run report: {e}")
    
    def _generate_rag_response(self, query: str) -> Dict[str, Any]:
        """
        Generate RAG response using existing system
        
        Returns:
            Dictionary with answer, contexts, and metadata
        """
        
        try:
            if self.retrieval_config is not None:
                # Tuning mode: run retrieval-only with custom params, then call LLM
                from evaluation.retrieval_tuner import RetrievalRunner
                runner = RetrievalRunner()
                docs = runner.run(query, self.retrieval_config)
                contexts = [
                    d.get("page_content", d.get("content", ""))
                    for d in docs
                    if d.get("page_content", d.get("content", "")).strip()
                ]
                # Still call process_with_ai for the answer, contexts come from tuner
                answer, answered, matched_files, performance = process_with_ai(
                    query,
                    session_id=f"eval_tune_{int(time.time())}"
                )
            else:
                # Normal mode: use existing query processor to generate response
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