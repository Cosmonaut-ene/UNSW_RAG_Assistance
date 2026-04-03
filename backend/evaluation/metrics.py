"""
RAG evaluation metrics using RAGAS framework
Implements comprehensive evaluation for the UNSW CSE chatbot RAG system
"""

import json
import math
import time
import traceback
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

import nest_asyncio
nest_asyncio.apply()

try:
    from ragas import evaluate
    from ragas.metrics import (
        Faithfulness,
        AnswerRelevancy,
        ContextRecall,
        ContextPrecision,
    )
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from datasets import Dataset

    # Configure RAGAS to use Gemini (LLM judge) + local HuggingFace embeddings
    import os
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_huggingface import HuggingFaceEmbeddings

    _ragas_llm = LangchainLLMWrapper(
        ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
    )
    # Use local embeddings to avoid Google Embedding API quota/availability issues
    _ragas_embeddings = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(
            model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    )

    faithfulness = Faithfulness(llm=_ragas_llm)
    answer_relevancy = AnswerRelevancy(llm=_ragas_llm, embeddings=_ragas_embeddings)
    context_recall = ContextRecall(llm=_ragas_llm)
    context_precision = ContextPrecision(llm=_ragas_llm)

    RAGAS_V2 = True
    RAGAS_AVAILABLE = True
except ImportError:
    print("RAGAS not available. Run: pip install ragas datasets")
    RAGAS_AVAILABLE = False
    RAGAS_V2 = False

from .config import RAGAS_CONFIG, PERFORMANCE_THRESHOLDS, EVALUATION_RESULTS_PATH


class RAGEvaluator:
    """Comprehensive RAG evaluation using RAGAS metrics"""
    
    def __init__(self, llm_temperature: float = 0.0):
        if not RAGAS_AVAILABLE:
            raise ImportError("RAGAS framework not available. Install with: pip install ragas datasets")
            
        self.metrics = [
            faithfulness,
            answer_relevancy,
            context_recall,
            context_precision
        ]
        self.llm_temperature = llm_temperature
        self.evaluation_results = []
        
    def evaluate_response(self,
                         query: str,
                         generated_answer: str,
                         retrieved_contexts: List[str],
                         ground_truth: str = None,
                         ground_truth_answer: str = None) -> Dict[str, Any]:
        """
        Evaluate a single RAG response using RAGAS metrics

        Args:
            query: Original user question
            generated_answer: RAG system generated response
            retrieved_contexts: List of retrieved document contexts
            ground_truth: Expected answer (RAGAS standard field name)
            ground_truth_answer: Deprecated alias for ground_truth

        Returns:
            Dictionary containing evaluation scores and metadata
        """
        # Unify field: prefer ground_truth, fall back to ground_truth_answer
        gt = ground_truth or ground_truth_answer

        start_time = time.time()

        try:
            # Prepare data for RAGAS evaluation
            eval_data = {
                "question": [query],
                "answer": [generated_answer],
                "contexts": [retrieved_contexts]
            }

            # Add ground truth if available (required for context_recall)
            if gt:
                eval_data["ground_truth"] = [gt]
                
            # Convert to HuggingFace Dataset
            dataset = Dataset.from_dict(eval_data)
            
            # Select metrics based on available data
            metrics_to_use = [faithfulness, answer_relevancy, context_precision]
            if gt:
                metrics_to_use.append(context_recall)
            
            # Run evaluation with Gemini as judge LLM
            result = evaluate(
                dataset,
                metrics=metrics_to_use,
                llm=_ragas_llm,
                embeddings=_ragas_embeddings,
            )
            
            # Extract scores — RAGAS v0.2+ returns EvaluationResult, not a dict.
            # Use to_pandas() to get per-sample scores, then average across the batch.
            scores = {}
            metric_keys = ['faithfulness', 'answer_relevancy', 'context_recall', 'context_precision']
            try:
                df = result.to_pandas()
                for metric_name in metric_keys:
                    if metric_name in df.columns:
                        val = df[metric_name].dropna().mean()
                        if not (val != val):  # NaN check
                            scores[metric_name] = float(val)
            except Exception:
                # Fallback: try dict-style access (older RAGAS versions)
                for metric_name in metric_keys:
                    try:
                        scores[metric_name] = float(result[metric_name])
                    except (KeyError, TypeError):
                        pass
            
            evaluation_time = time.time() - start_time
            
            # Create evaluation result
            eval_result = {
                "query": query,
                "generated_answer": generated_answer,
                "retrieved_contexts": retrieved_contexts,
                "ground_truth": gt,
                "scores": scores,
                "performance_analysis": self._analyze_performance(scores),
                "evaluation_metadata": {
                    "evaluation_time_seconds": round(evaluation_time, 3),
                    "timestamp": datetime.now().isoformat(),
                    "num_contexts": len(retrieved_contexts),
                    "answer_length": len(generated_answer.split()),
                    "ragas_version": "0.2+" if RAGAS_V2 else "0.1.x"
                }
            }
            
            return eval_result
            
        except Exception as e:
            print(f"Error in RAG evaluation: {e}")
            traceback.print_exc()
            return {
                "query": query,
                "generated_answer": generated_answer,
                "error": str(e),
                "scores": {},
                "evaluation_metadata": {
                    "evaluation_time_seconds": time.time() - start_time,
                    "timestamp": datetime.now().isoformat(),
                    "error": True
                }
            }
    
    def evaluate_batch(self, 
                      evaluation_data: List[Dict[str, Any]],
                      batch_size: int = 10) -> Dict[str, Any]:
        """
        Evaluate a batch of RAG responses
        
        Args:
            evaluation_data: List of evaluation examples with keys:
                - query: User question
                - generated_answer: RAG response  
                - retrieved_contexts: List of context strings
                - ground_truth_answer: Expected answer (optional)
            batch_size: Number of evaluations to process at once
            
        Returns:
            Comprehensive evaluation report
        """
        
        print(f"Starting batch evaluation of {len(evaluation_data)} examples...")
        batch_start_time = time.time()
        
        individual_results = []
        successful_evaluations = 0
        failed_evaluations = 0
        
        # Process in batches
        for i in range(0, len(evaluation_data), batch_size):
            batch = evaluation_data[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(evaluation_data) + batch_size - 1)//batch_size}")
            
            for item in batch:
                try:
                    result = self.evaluate_response(
                        query=item["query"],
                        generated_answer=item["generated_answer"],
                        retrieved_contexts=item["retrieved_contexts"],
                        ground_truth=item.get("ground_truth", item.get("ground_truth_answer", item.get("expected_answer")))
                    )
                    
                    if "error" not in result:
                        successful_evaluations += 1
                    else:
                        failed_evaluations += 1
                        
                    individual_results.append(result)
                    
                except Exception as e:
                    print(f"Failed to evaluate item: {e}")
                    failed_evaluations += 1
                    individual_results.append({
                        "query": item.get("query", "Unknown"),
                        "error": str(e),
                        "scores": {}
                    })
        
        # Calculate aggregate metrics
        aggregate_scores = self._calculate_aggregate_scores(individual_results)
        evaluation_time = time.time() - batch_start_time
        
        # Create comprehensive report
        evaluation_report = {
            "summary": {
                "total_evaluations": len(evaluation_data),
                "successful_evaluations": successful_evaluations,
                "failed_evaluations": failed_evaluations,
                "success_rate": successful_evaluations / len(evaluation_data) if evaluation_data else 0,
                "total_evaluation_time_seconds": round(evaluation_time, 3),
                "average_time_per_evaluation": round(evaluation_time / len(evaluation_data), 3) if evaluation_data else 0
            },
            "aggregate_scores": aggregate_scores,
            "performance_analysis": self._analyze_batch_performance(aggregate_scores),
            "individual_results": individual_results,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "ragas_config": RAGAS_CONFIG,
                "evaluation_version": "1.0"
            }
        }
        
        # Store results
        self.evaluation_results.append(evaluation_report)
        
        return evaluation_report
    
    def _calculate_aggregate_scores(self, results: List[Dict]) -> Dict[str, float]:
        """Calculate aggregate scores across all evaluations"""
        
        score_sums = {}
        score_counts = {}
        
        for result in results:
            if "scores" in result and result["scores"]:
                for metric, score in result["scores"].items():
                    if isinstance(score, (int, float)) and not (isinstance(score, float) and math.isnan(score)):
                        if metric not in score_sums:
                            score_sums[metric] = 0
                            score_counts[metric] = 0
                        score_sums[metric] += score
                        score_counts[metric] += 1
        
        # Calculate averages
        aggregate_scores = {}
        for metric in score_sums:
            if score_counts[metric] > 0:
                aggregate_scores[metric] = round(score_sums[metric] / score_counts[metric], 4)
                aggregate_scores[f"{metric}_count"] = score_counts[metric]
        
        return aggregate_scores
    
    def _analyze_performance(self, scores: Dict[str, float]) -> Dict[str, str]:
        """Analyze performance level for individual evaluation"""
        
        analysis = {}
        
        for metric, score in scores.items():
            if metric in PERFORMANCE_THRESHOLDS:
                thresholds = PERFORMANCE_THRESHOLDS[metric]
                
                if score >= thresholds["excellent"]:
                    analysis[metric] = "excellent"
                elif score >= thresholds["good"]:
                    analysis[metric] = "good"
                elif score >= thresholds["acceptable"]:
                    analysis[metric] = "acceptable"
                else:
                    analysis[metric] = "poor"
        
        return analysis
    
    def _analyze_batch_performance(self, aggregate_scores: Dict[str, float]) -> Dict[str, Any]:
        """Analyze overall batch performance"""
        
        analysis = {
            "overall_performance": "good",
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }
        
        metric_scores = {k: v for k, v in aggregate_scores.items() if not k.endswith('_count')}
        
        if not metric_scores:
            analysis["overall_performance"] = "unknown"
            analysis["recommendations"].append("No valid scores to analyze")
            return analysis
        
        # Analyze each metric
        for metric, score in metric_scores.items():
            if metric in PERFORMANCE_THRESHOLDS:
                thresholds = PERFORMANCE_THRESHOLDS[metric]
                
                if score >= thresholds["excellent"]:
                    analysis["strengths"].append(f"Excellent {metric.replace('_', ' ')}: {score:.3f}")
                elif score >= thresholds["good"]:
                    analysis["strengths"].append(f"Good {metric.replace('_', ' ')}: {score:.3f}")
                elif score >= thresholds["acceptable"]:
                    pass  # Neutral
                else:
                    analysis["weaknesses"].append(f"Poor {metric.replace('_', ' ')}: {score:.3f}")
        
        # Overall performance assessment
        avg_score = sum(metric_scores.values()) / len(metric_scores)
        if avg_score >= 0.85:
            analysis["overall_performance"] = "excellent"
        elif avg_score >= 0.75:
            analysis["overall_performance"] = "good"
        elif avg_score >= 0.65:
            analysis["overall_performance"] = "acceptable"
        else:
            analysis["overall_performance"] = "needs_improvement"
        
        # Generate recommendations
        if "faithfulness" in metric_scores and metric_scores["faithfulness"] < 0.7:
            analysis["recommendations"].append("Improve faithfulness by enhancing context relevance and reducing hallucinations")
            
        if "answer_relevancy" in metric_scores and metric_scores["answer_relevancy"] < 0.7:
            analysis["recommendations"].append("Improve answer relevancy by better query understanding and response generation")
            
        if "context_recall" in metric_scores and metric_scores["context_recall"] < 0.7:
            analysis["recommendations"].append("Improve context recall by enhancing retrieval coverage")
            
        if "context_precision" in metric_scores and metric_scores["context_precision"] < 0.7:
            analysis["recommendations"].append("Improve context precision by reducing noise in retrieved contexts")
        
        return analysis
    
    def save_results(self, filepath: str = None):
        """Save evaluation results to file"""
        
        if filepath is None:
            filepath = EVALUATION_RESULTS_PATH
            
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.evaluation_results, f, indent=2, ensure_ascii=False)
            print(f"Evaluation results saved to {filepath}")
        except Exception as e:
            print(f"Error saving evaluation results: {e}")
    
    def load_results(self, filepath: str = None):
        """Load evaluation results from file"""
        
        if filepath is None:
            filepath = EVALUATION_RESULTS_PATH
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.evaluation_results = json.load(f)
            print(f"Evaluation results loaded from {filepath}")
        except Exception as e:
            print(f"Error loading evaluation results: {e}")
    
    def generate_report_summary(self) -> str:
        """Generate a human-readable evaluation summary"""
        
        if not self.evaluation_results:
            return "No evaluation results available"
        
        latest_result = self.evaluation_results[-1]
        summary = latest_result["summary"]
        aggregate = latest_result["aggregate_scores"]
        analysis = latest_result["performance_analysis"]
        
        report = f"""
RAG Evaluation Report Summary
============================

Evaluation Overview:
- Total Evaluations: {summary['total_evaluations']}
- Success Rate: {summary['success_rate']:.1%}
- Total Time: {summary['total_evaluation_time_seconds']:.1f}s
- Average Time per Evaluation: {summary['average_time_per_evaluation']:.3f}s

Performance Scores:
"""
        
        for metric, score in aggregate.items():
            if not metric.endswith('_count'):
                report += f"- {metric.replace('_', ' ').title()}: {score:.3f}\n"
        
        report += f"""
Overall Performance: {analysis['overall_performance'].title()}

Strengths:
"""
        for strength in analysis.get('strengths', []):
            report += f"- {strength}\n"
        
        if analysis.get('weaknesses'):
            report += "\nWeaknesses:\n"
            for weakness in analysis['weaknesses']:
                report += f"- {weakness}\n"
        
        if analysis.get('recommendations'):
            report += "\nRecommendations:\n"
            for rec in analysis['recommendations']:
                report += f"- {rec}\n"
        
        return report
