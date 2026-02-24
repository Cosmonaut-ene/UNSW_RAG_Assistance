"""
Unit tests for evaluation pipeline
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
import tempfile
import json
from pathlib import Path

from evaluation.pipeline import EvaluationPipeline


class TestEvaluationPipeline:
    """Test evaluation pipeline functionality"""
    
    @pytest.fixture
    def pipeline(self):
        """Create a test pipeline instance"""
        with patch('evaluation.pipeline.RAGEvaluator') as mock_evaluator_class, \
             patch('evaluation.pipeline.EvaluationDataset') as mock_dataset_class:
            
            # Mock evaluator
            mock_evaluator = MagicMock()
            mock_evaluator_class.return_value = mock_evaluator
            
            # Mock dataset
            mock_dataset = MagicMock()
            mock_dataset.test_queries = []
            mock_dataset_class.return_value = mock_dataset
            
            pipeline = EvaluationPipeline(use_hybrid_search=True)
            pipeline.evaluator = mock_evaluator
            pipeline.dataset = mock_dataset
            
            return pipeline
    
    @pytest.fixture
    def mock_test_queries(self):
        """Create mock test queries"""
        return [
            {
                "query": "What is COMP9900?",
                "expected_answer": "COMP9900 is a capstone project course.",
                "category": "course_information",
                "difficulty": "easy",
                "query_type": "direct"
            },
            {
                "query": "What are the prerequisites for COMP9900?",
                "expected_answer": "Prerequisites include COMP2511 and COMP3311.",
                "category": "prerequisites",
                "difficulty": "medium", 
                "query_type": "direct"
            }
        ]
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization"""
        with patch('evaluation.pipeline.RAGEvaluator'), \
             patch('evaluation.pipeline.EvaluationDataset'):
            
            pipeline = EvaluationPipeline(use_hybrid_search=False)
            assert pipeline.use_hybrid_search is False
            assert pipeline.evaluation_results == []
    
    @patch('evaluation.pipeline.process_with_ai')
    @patch('evaluation.pipeline.load_vector_store')
    @patch('evaluation.pipeline.search_documents_with_scores')
    def test_generate_rag_response(self, mock_search, mock_load_vector, mock_process, pipeline):
        """Test RAG response generation"""
        
        # Mock process_with_ai response
        mock_process.return_value = (
            "COMP9900 is a capstone project course.",  # answer
            True,  # answered
            ["handbook.pdf"],  # matched_files
            {"response_time_ms": 500}  # performance
        )
        
        # Mock vector store and search
        mock_vector_store = MagicMock()
        mock_load_vector.return_value = mock_vector_store
        
        mock_doc1 = MagicMock()
        mock_doc1.page_content = "COMP9900 course description"
        mock_doc2 = MagicMock()
        mock_doc2.page_content = "Capstone project requirements"
        
        mock_search.return_value = [(mock_doc1, 0.9), (mock_doc2, 0.8)]
        
        query = "What is COMP9900?"
        response = pipeline._generate_rag_response(query)
        
        # Verify response structure
        assert "answer" in response
        assert "contexts" in response
        assert "metadata" in response
        
        assert response["answer"] == "COMP9900 is a capstone project course."
        assert len(response["contexts"]) > 0
        assert "COMP9900 course description" in response["contexts"]
        
        # Verify metadata
        metadata = response["metadata"]
        assert metadata["answered"] is True
        assert metadata["matched_files"] == ["handbook.pdf"]
        assert "performance" in metadata
    
    @patch('evaluation.pipeline.process_with_ai')
    def test_generate_rag_response_error_handling(self, mock_process, pipeline):
        """Test error handling in RAG response generation"""
        
        # Mock process_with_ai to raise an error
        mock_process.side_effect = Exception("RAG processing error")
        
        query = "What is COMP9900?"
        response = pipeline._generate_rag_response(query)
        
        # Should handle error gracefully
        assert "Error:" in response["answer"]
        assert response["contexts"] == []
        assert "error" in response["metadata"]
    
    def test_run_comprehensive_evaluation(self, pipeline, mock_test_queries):
        """Test comprehensive evaluation run"""
        
        # Setup mock dataset
        pipeline.dataset.test_queries = mock_test_queries
        pipeline.dataset.load_datasets = MagicMock()
        pipeline.dataset.create_unsw_ground_truth = MagicMock()
        pipeline.dataset.generate_test_queries = MagicMock(return_value=mock_test_queries)
        pipeline.dataset.save_datasets = MagicMock()
        
        # Mock RAG response generation
        pipeline._generate_rag_response = MagicMock(return_value={
            "answer": "Test answer",
            "contexts": ["Test context 1", "Test context 2"],
            "metadata": {"answered": True, "performance": {}}
        })
        
        # Mock evaluator
        pipeline.evaluator.evaluate_batch = MagicMock(return_value={
            "summary": {
                "total_evaluations": 2,
                "successful_evaluations": 2,
                "success_rate": 1.0
            },
            "aggregate_scores": {
                "faithfulness": 0.85,
                "answer_relevancy": 0.80
            },
            "performance_analysis": {"overall_performance": "good"},
            "individual_results": []
        })
        
        # Run evaluation
        result = pipeline.run_comprehensive_evaluation(sample_size=2)
        
        # Verify result structure
        assert "summary" in result
        assert "aggregate_scores" in result
        assert "performance_analysis" in result
        assert "pipeline_metadata" in result
        
        # Verify pipeline metadata
        pipeline_meta = result["pipeline_metadata"]
        assert "total_pipeline_time_seconds" in pipeline_meta
        assert pipeline_meta["use_hybrid_search"] is True
        assert pipeline_meta["actual_queries_tested"] == 2
        
        # Verify evaluator was called
        pipeline.evaluator.evaluate_batch.assert_called_once()
        
        # Verify results stored
        assert len(pipeline.evaluation_results) == 1
    
    def test_run_category_analysis(self, pipeline):
        """Test category-based evaluation analysis"""
        
        # Mock comprehensive evaluation
        pipeline.run_comprehensive_evaluation = MagicMock(return_value={
            "aggregate_scores": {"faithfulness": 0.8},
            "performance_analysis": {"overall_performance": "good"},
            "summary": {"total_evaluations": 5}
        })
        
        result = pipeline.run_category_analysis()
        
        # Verify result structure
        assert "category_analysis" in result
        assert "timestamp" in result
        assert result["analysis_type"] == "by_category"
        
        # Should have called comprehensive evaluation multiple times
        assert pipeline.run_comprehensive_evaluation.call_count > 0
    
    def test_run_difficulty_analysis(self, pipeline, mock_test_queries):
        """Test difficulty-based evaluation analysis"""
        
        # Setup mock dataset with difficulty queries
        pipeline.dataset.get_queries_by_difficulty = MagicMock(return_value=mock_test_queries[:1])
        
        # Mock RAG response generation
        pipeline._generate_rag_response = MagicMock(return_value={
            "answer": "Test answer",
            "contexts": ["Test context"],
            "metadata": {}
        })
        
        # Mock evaluator
        pipeline.evaluator.evaluate_batch = MagicMock(return_value={
            "aggregate_scores": {"faithfulness": 0.75},
            "performance_analysis": {"overall_performance": "acceptable"},
            "summary": {"total_evaluations": 1}
        })
        
        result = pipeline.run_difficulty_analysis()
        
        # Verify result structure
        assert "difficulty_analysis" in result
        assert "timestamp" in result
        assert result["analysis_type"] == "by_difficulty"
        
        # Should have called get_queries_by_difficulty for each difficulty level
        expected_calls = ["easy", "medium", "hard"]
        actual_calls = [call.args[0] for call in pipeline.dataset.get_queries_by_difficulty.call_args_list]
        for difficulty in expected_calls:
            assert difficulty in actual_calls
    
    def test_run_ab_test(self, pipeline, mock_test_queries):
        """Test A/B testing functionality"""
        
        # Mock comprehensive evaluation
        pipeline.run_comprehensive_evaluation = MagicMock(return_value={
            "aggregate_scores": {"faithfulness": 0.8},
            "performance_analysis": {"overall_performance": "good"},
            "summary": {"total_evaluations": 20}
        })
        
        # Test hybrid search
        original_mode = pipeline.use_hybrid_search
        result = pipeline.run_ab_test(use_hybrid=True)
        
        # Verify result structure
        assert result["search_mode"] == "hybrid"
        assert "test_results" in result
        assert "timestamp" in result
        
        # Verify mode was temporarily changed and restored
        assert pipeline.use_hybrid_search == original_mode
        
        # Verify comprehensive evaluation was called
        pipeline.run_comprehensive_evaluation.assert_called_with(sample_size=20)
    
    def test_generate_performance_comparison(self, pipeline):
        """Test performance comparison between two runs"""
        
        baseline_results = {
            "aggregate_scores": {
                "faithfulness": 0.80,
                "answer_relevancy": 0.75,
                "context_recall": 0.70
            }
        }
        
        current_results = {
            "aggregate_scores": {
                "faithfulness": 0.85,
                "answer_relevancy": 0.72,
                "context_recall": 0.78
            }
        }
        
        comparison = pipeline.generate_performance_comparison(baseline_results, current_results)
        
        # Verify comparison structure
        assert "comparison_type" in comparison
        assert "metrics_comparison" in comparison
        assert comparison["comparison_type"] == "performance_delta"
        
        # Verify metric comparisons
        metrics = comparison["metrics_comparison"]
        
        # Faithfulness improved
        assert metrics["faithfulness"]["baseline"] == 0.80
        assert metrics["faithfulness"]["current"] == 0.85
        assert metrics["faithfulness"]["delta"] == 0.05
        assert metrics["faithfulness"]["improvement"] is True
        
        # Answer relevancy declined
        assert metrics["answer_relevancy"]["improvement"] is False
        assert metrics["answer_relevancy"]["delta"] < 0
        
        # Context recall improved
        assert metrics["context_recall"]["improvement"] is True
    
    def test_save_pipeline_results(self, pipeline):
        """Test saving pipeline results"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_pipeline_results.json"
            
            # Add some test results
            pipeline.evaluation_results = [
                {"test": "evaluation1", "scores": {"faithfulness": 0.8}},
                {"test": "evaluation2", "scores": {"faithfulness": 0.9}}
            ]
            
            # Save results
            pipeline.save_pipeline_results(str(test_file))
            
            # Verify file was created and contains correct data
            assert test_file.exists()
            
            with open(test_file, 'r') as f:
                saved_data = json.load(f)
                
            assert len(saved_data) == 2
            assert saved_data[0]["test"] == "evaluation1"
            assert saved_data[1]["scores"]["faithfulness"] == 0.9
    
    def test_get_latest_results(self, pipeline):
        """Test getting latest evaluation results"""
        
        # Test with no results
        assert pipeline.get_latest_results() is None
        
        # Add some results
        pipeline.evaluation_results = [
            {"timestamp": "2025-01-01T10:00:00", "score": 0.8},
            {"timestamp": "2025-01-01T11:00:00", "score": 0.9}
        ]
        
        latest = pipeline.get_latest_results()
        assert latest["score"] == 0.9
        assert latest["timestamp"] == "2025-01-01T11:00:00"
    
    def test_category_filtering(self, pipeline, mock_test_queries):
        """Test query filtering by categories"""
        
        # Add category info to mock queries
        mock_test_queries[0]["category"] = "course_information"
        mock_test_queries[1]["category"] = "prerequisites"
        
        pipeline.dataset.test_queries = mock_test_queries
        pipeline.dataset.load_datasets = MagicMock()
        
        # Mock other dependencies
        pipeline._generate_rag_response = MagicMock(return_value={
            "answer": "Test answer",
            "contexts": ["Test context"],
            "metadata": {}
        })
        
        pipeline.evaluator.evaluate_batch = MagicMock(return_value={
            "summary": {"total_evaluations": 1},
            "aggregate_scores": {},
            "performance_analysis": {},
            "individual_results": []
        })
        
        # Run evaluation with category filter
        result = pipeline.run_comprehensive_evaluation(
            sample_size=10,
            categories=["course_information"]
        )
        
        # Verify only course_information queries were processed
        call_args = pipeline.evaluator.evaluate_batch.call_args[0][0]
        assert len(call_args) == 1  # Only one query matches category
        
        # Verify pipeline metadata reflects the filter
        assert result["pipeline_metadata"]["categories_tested"] == ["course_information"]
    
    def test_hybrid_search_integration(self, pipeline):
        """Test integration with hybrid search functionality"""
        
        pipeline.use_hybrid_search = True
        
        with patch('evaluation.pipeline.HybridSearchEngine') as mock_hybrid_class:
            mock_hybrid_engine = MagicMock()
            mock_hybrid_results = [
                {"page_content": "Hybrid context 1", "metadata": {"score": 0.9}},
                {"page_content": "Hybrid context 2", "metadata": {"score": 0.8}}
            ]
            mock_hybrid_engine.search_hybrid.return_value = mock_hybrid_results
            mock_hybrid_class.return_value = mock_hybrid_engine
            
            with patch('evaluation.pipeline.process_with_ai') as mock_process, \
                 patch('evaluation.pipeline.load_vector_store') as mock_load_vector, \
                 patch('evaluation.pipeline.search_documents_with_scores') as mock_search:
                
                # Mock dependencies
                mock_process.return_value = ("Answer", True, [], {})
                mock_vector_store = MagicMock()
                mock_load_vector.return_value = mock_vector_store
                mock_search.return_value = []
                
                response = pipeline._generate_rag_response("Test query")
                
                # Verify hybrid search was used
                mock_hybrid_class.assert_called_once_with(mock_vector_store)
                mock_hybrid_engine.search_hybrid.assert_called_once()
                
                # Verify hybrid contexts were included
                assert "Hybrid context 1" in response["contexts"]
                assert "Hybrid context 2" in response["contexts"]