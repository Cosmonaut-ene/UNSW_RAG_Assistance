"""
Unit tests for RAG evaluation metrics
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
import json
import tempfile
from pathlib import Path

# Mock RAGAS imports to handle cases where it's not installed
with patch.dict('sys.modules', {
    'ragas': MagicMock(),
    'ragas.metrics': MagicMock(),
    'datasets': MagicMock()
}):
    from evaluation.metrics import RAGEvaluator


class TestRAGEvaluator:
    """Test RAG evaluation metrics functionality"""
    
    @pytest.fixture
    def evaluator(self):
        """Create a test evaluator instance with mocked RAGAS"""
        with patch('evaluation.metrics.RAGAS_AVAILABLE', True):
            return RAGEvaluator()
    
    @pytest.fixture
    def mock_ragas_result(self):
        """Mock RAGAS evaluation result"""
        return {
            'faithfulness': 0.85,
            'answer_relevancy': 0.78,
            'context_recall': 0.90,
            'context_precision': 0.72
        }
    
    def test_evaluator_initialization(self):
        """Test evaluator initialization"""
        with patch('evaluation.metrics.RAGAS_AVAILABLE', True):
            evaluator = RAGEvaluator(llm_temperature=0.1)
            assert evaluator.llm_temperature == 0.1
            assert evaluator.evaluation_results == []
    
    def test_evaluator_initialization_without_ragas(self):
        """Test evaluator initialization when RAGAS is not available"""
        with patch('evaluation.metrics.RAGAS_AVAILABLE', False):
            with pytest.raises(ImportError, match="RAGAS framework not available"):
                RAGEvaluator()
    
    @patch('evaluation.metrics.evaluate')
    @patch('evaluation.metrics.Dataset')
    def test_evaluate_response_success(self, mock_dataset, mock_evaluate, evaluator, mock_ragas_result):
        """Test successful single response evaluation"""
        
        # Mock dataset creation
        mock_dataset_instance = MagicMock()
        mock_dataset.from_dict.return_value = mock_dataset_instance
        
        # Mock evaluation result
        mock_evaluate.return_value = mock_ragas_result
        
        # Test data
        query = "What is COMP9900?"
        answer = "COMP9900 is a capstone project course."
        contexts = ["COMP9900 course description", "Capstone project requirements"]
        ground_truth = "COMP9900 is a software engineering capstone project."
        
        result = evaluator.evaluate_response(query, answer, contexts, ground_truth)
        
        # Verify result structure
        assert "query" in result
        assert "generated_answer" in result
        assert "retrieved_contexts" in result
        assert "ground_truth" in result
        assert "scores" in result
        assert "performance_analysis" in result
        assert "evaluation_metadata" in result
        
        # Verify scores
        assert result["scores"]["faithfulness"] == 0.85
        assert result["scores"]["answer_relevancy"] == 0.78
        assert result["scores"]["context_recall"] == 0.90
        assert result["scores"]["context_precision"] == 0.72
        
        # Verify metadata
        assert "evaluation_time_seconds" in result["evaluation_metadata"]
        assert "timestamp" in result["evaluation_metadata"]
        assert result["evaluation_metadata"]["num_contexts"] == 2
        assert result["evaluation_metadata"]["answer_length"] > 0
    
    @patch('evaluation.metrics.evaluate')
    @patch('evaluation.metrics.Dataset')
    def test_evaluate_response_without_ground_truth(self, mock_dataset, mock_evaluate, evaluator):
        """Test evaluation without ground truth (no context_recall)"""
        
        # Mock dataset and evaluation
        mock_dataset.from_dict.return_value = MagicMock()
        mock_evaluate.return_value = {
            'faithfulness': 0.80,
            'answer_relevancy': 0.75,
            'context_precision': 0.70
        }
        
        query = "What is COMP9900?"
        answer = "COMP9900 is a capstone project course."
        contexts = ["COMP9900 course description"]
        
        result = evaluator.evaluate_response(query, answer, contexts)
        
        # Should not have context_recall without ground truth
        assert "faithfulness" in result["scores"]
        assert "answer_relevancy" in result["scores"]
        assert "context_precision" in result["scores"]
        assert result["ground_truth"] is None
    
    @patch('evaluation.metrics.evaluate')
    def test_evaluate_response_error_handling(self, mock_evaluate, evaluator):
        """Test error handling in evaluation"""
        
        # Mock evaluation to raise an error
        mock_evaluate.side_effect = Exception("API Error")
        
        query = "What is COMP9900?"
        answer = "COMP9900 is a capstone project course."
        contexts = ["COMP9900 course description"]
        
        result = evaluator.evaluate_response(query, answer, contexts)
        
        # Should return error result
        assert "error" in result
        assert "API Error" in result["error"]
        assert result["scores"] == {}
        assert result["evaluation_metadata"]["error"] is True
    
    @patch('evaluation.metrics.evaluate')
    @patch('evaluation.metrics.Dataset')
    def test_evaluate_batch(self, mock_dataset, mock_evaluate, evaluator, mock_ragas_result):
        """Test batch evaluation functionality"""
        
        # Mock dataset and evaluation
        mock_dataset.from_dict.return_value = MagicMock()
        mock_evaluate.return_value = mock_ragas_result
        
        # Prepare test data
        evaluation_data = [
            {
                "query": "What is COMP9900?",
                "generated_answer": "COMP9900 is a capstone project course.",
                "retrieved_contexts": ["Context 1"],
                "ground_truth_answer": "Ground truth answer 1"
            },
            {
                "query": "What are prerequisites?", 
                "generated_answer": "Prerequisites include COMP2511.",
                "retrieved_contexts": ["Context 2"],
                "ground_truth_answer": "Ground truth answer 2"
            }
        ]
        
        result = evaluator.evaluate_batch(evaluation_data)
        
        # Verify batch result structure
        assert "summary" in result
        assert "aggregate_scores" in result
        assert "performance_analysis" in result
        assert "individual_results" in result
        assert "metadata" in result
        
        # Verify summary
        summary = result["summary"]
        assert summary["total_evaluations"] == 2
        assert summary["successful_evaluations"] <= 2
        assert "success_rate" in summary
        assert "total_evaluation_time_seconds" in summary
        
        # Verify individual results
        assert len(result["individual_results"]) == 2
    
    def test_calculate_aggregate_scores(self, evaluator):
        """Test aggregate score calculation"""
        
        # Mock individual results
        individual_results = [
            {"scores": {"faithfulness": 0.8, "answer_relevancy": 0.7}},
            {"scores": {"faithfulness": 0.9, "answer_relevancy": 0.8}},
            {"scores": {"faithfulness": 0.7, "answer_relevancy": 0.9}}
        ]
        
        aggregate = evaluator._calculate_aggregate_scores(individual_results)
        
        # Should calculate averages correctly
        assert abs(aggregate["faithfulness"] - 0.8) < 0.01  # (0.8 + 0.9 + 0.7) / 3
        assert abs(aggregate["answer_relevancy"] - 0.8) < 0.01  # (0.7 + 0.8 + 0.9) / 3
        assert aggregate["faithfulness_count"] == 3
        assert aggregate["answer_relevancy_count"] == 3
    
    def test_analyze_performance(self, evaluator):
        """Test performance analysis"""
        
        # Test excellent scores
        scores = {
            "faithfulness": 0.95,
            "answer_relevancy": 0.92,
            "context_recall": 0.88,
            "context_precision": 0.90
        }
        
        analysis = evaluator._analyze_performance(scores)
        
        assert analysis["faithfulness"] == "excellent"
        assert analysis["answer_relevancy"] == "excellent"
        assert analysis["context_recall"] == "good"
        assert analysis["context_precision"] == "excellent"
    
    def test_analyze_batch_performance(self, evaluator):
        """Test batch performance analysis"""
        
        aggregate_scores = {
            "faithfulness": 0.85,
            "answer_relevancy": 0.80,
            "context_recall": 0.75,
            "context_precision": 0.70
        }
        
        analysis = evaluator._analyze_batch_performance(aggregate_scores)
        
        assert "overall_performance" in analysis
        assert "strengths" in analysis
        assert "weaknesses" in analysis
        assert "recommendations" in analysis
        
        # Should identify strengths and provide recommendations
        assert isinstance(analysis["strengths"], list)
        assert isinstance(analysis["recommendations"], list)
    
    def test_save_and_load_results(self, evaluator):
        """Test saving and loading evaluation results"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_results.json"
            
            # Add some test results
            evaluator.evaluation_results = [
                {"test": "result1", "score": 0.8},
                {"test": "result2", "score": 0.9}
            ]
            
            # Save results
            evaluator.save_results(str(test_file))
            assert test_file.exists()
            
            # Load results into new evaluator
            new_evaluator = RAGEvaluator() if hasattr(RAGEvaluator, '__init__') else Mock()
            if hasattr(new_evaluator, 'load_results'):
                new_evaluator.evaluation_results = []
                new_evaluator.load_results(str(test_file))
                assert len(new_evaluator.evaluation_results) == 2
    
    def test_generate_report_summary(self, evaluator):
        """Test report summary generation"""
        
        # Mock evaluation results
        evaluator.evaluation_results = [{
            "summary": {
                "total_evaluations": 10,
                "successful_evaluations": 9,
                "failed_evaluations": 1,
                "success_rate": 0.9,
                "total_evaluation_time_seconds": 45.5,
                "average_time_per_evaluation": 4.55
            },
            "aggregate_scores": {
                "faithfulness": 0.85,
                "answer_relevancy": 0.78,
                "context_recall": 0.82,
                "context_precision": 0.75
            },
            "performance_analysis": {
                "overall_performance": "good",
                "strengths": ["Good faithfulness: 0.850"],
                "weaknesses": ["Poor context precision: 0.750"],
                "recommendations": ["Improve context precision"]
            }
        }]
        
        summary = evaluator.generate_report_summary()
        
        assert isinstance(summary, str)
        assert "RAG Evaluation Report Summary" in summary
        assert "Total Evaluations: 10" in summary
        assert "Success Rate: 90.0%" in summary
        assert "Faithfulness: 0.850" in summary
        assert "Overall Performance: Good" in summary
    
    def test_performance_thresholds(self, evaluator):
        """Test performance threshold classifications"""
        
        # Test different score ranges
        test_cases = [
            (0.95, "excellent"),
            (0.85, "good"),
            (0.75, "acceptable"),
            (0.65, "poor"),
            (0.55, "poor")
        ]
        
        for score, expected_level in test_cases:
            scores = {"faithfulness": score}
            analysis = evaluator._analyze_performance(scores)
            assert analysis["faithfulness"] == expected_level
    
    def test_empty_evaluation_data_handling(self, evaluator):
        """Test handling of empty evaluation data"""
        
        # Test with empty list
        result = evaluator.evaluate_batch([])
        
        assert result["summary"]["total_evaluations"] == 0
        assert result["summary"]["successful_evaluations"] == 0
        assert result["summary"]["success_rate"] == 0
        assert result["aggregate_scores"] == {}
    
    def test_malformed_evaluation_data(self, evaluator):
        """Test handling of malformed evaluation data"""
        
        # Test with missing required fields
        malformed_data = [
            {"query": "What is COMP9900?"},  # Missing other required fields
            {
                "generated_answer": "Answer without query",
                "retrieved_contexts": []
            }
        ]
        
        # Should handle gracefully without crashing
        try:
            result = evaluator.evaluate_batch(malformed_data)
            assert "summary" in result
        except Exception as e:
            # If it does raise an exception, it should be handled gracefully
            assert "evaluation" in str(e).lower() or "error" in str(e).lower()