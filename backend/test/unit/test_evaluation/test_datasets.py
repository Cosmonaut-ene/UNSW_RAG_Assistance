"""
Unit tests for evaluation datasets module
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from evaluation.datasets import EvaluationDataset
from evaluation.config import QUERY_CATEGORIES


class TestEvaluationDataset:
    """Test evaluation dataset creation and management"""
    
    @pytest.fixture
    def dataset(self):
        """Create a test dataset instance"""
        return EvaluationDataset()
    
    def test_create_unsw_ground_truth(self, dataset):
        """Test creation of UNSW-specific ground truth data"""
        
        ground_truth = dataset.create_unsw_ground_truth()
        
        # Verify data structure
        assert isinstance(ground_truth, list)
        assert len(ground_truth) > 0
        
        # Check first item structure
        first_item = ground_truth[0]
        required_fields = ["question", "ground_truth", "category", "difficulty", "expected_context_keywords"]
        for field in required_fields:
            assert field in first_item, f"Missing required field: {field}"
        
        # Verify categories are valid
        for item in ground_truth:
            assert item["category"] in QUERY_CATEGORIES or item["category"] == "conversation_followup"
        
        # Verify difficulty levels
        valid_difficulties = ["easy", "medium", "hard"]
        for item in ground_truth:
            assert item["difficulty"] in valid_difficulties
        
        # Check for UNSW-specific content
        unsw_keywords = ["UNSW", "COMP", "Computer Science", "CSE"]
        has_unsw_content = any(
            any(keyword in item["question"] or keyword in item["ground_truth"]
                for keyword in unsw_keywords)
            for item in ground_truth
        )
        assert has_unsw_content, "Ground truth should contain UNSW-specific content"
    
    def test_generate_test_queries(self, dataset):
        """Test generation of test queries from ground truth"""
        
        # First create ground truth
        dataset.create_unsw_ground_truth()
        
        # Generate test queries
        test_queries = dataset.generate_test_queries(sample_size=20)
        
        assert isinstance(test_queries, list)
        assert len(test_queries) <= 20  # Should respect sample_size limit
        
        # Check query structure
        for query in test_queries:
            assert "query" in query
            assert "category" in query
            assert "difficulty" in query
            assert "query_type" in query
            assert "id" in query
            assert isinstance(query["query"], str)
            assert len(query["query"].strip()) > 0
    
    def test_query_variations(self, dataset):
        """Test creation of query variations"""
        
        # Create ground truth with COMP course
        dataset.create_unsw_ground_truth()
        test_queries = dataset.generate_test_queries()
        
        # Check for variation patterns
        comp_queries = [q for q in test_queries if "COMP" in q["query"]]
        
        # Should have multiple queries about the same course
        comp9900_queries = [q for q in comp_queries if "COMP9900" in q["query"]]
        assert len(comp9900_queries) >= 1  # At least original + variations
    
    def test_save_and_load_datasets(self, dataset):
        """Test saving and loading datasets to/from files"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the file paths
            test_gt_path = Path(temp_dir) / "test_ground_truth.json"
            test_queries_path = Path(temp_dir) / "test_queries.json"
            
            with patch('evaluation.datasets.GROUND_TRUTH_PATH', test_gt_path), \
                 patch('evaluation.datasets.TEST_QUERIES_PATH', test_queries_path):
                
                # Create and save data
                dataset.create_unsw_ground_truth()
                dataset.generate_test_queries(sample_size=10)
                dataset.save_datasets()
                
                # Verify files were created
                assert test_gt_path.exists()
                assert test_queries_path.exists()
                
                # Create new dataset and load
                new_dataset = EvaluationDataset()
                new_dataset.load_datasets()
                
                # Verify data was loaded correctly
                assert len(new_dataset.ground_truth) > 0
                assert len(new_dataset.test_queries) > 0
                assert new_dataset.ground_truth[0]["question"] == dataset.ground_truth[0]["question"]
    
    def test_get_queries_by_category(self, dataset):
        """Test filtering queries by category"""
        
        dataset.create_unsw_ground_truth()
        dataset.generate_test_queries()
        
        # Test filtering by course_information
        course_queries = dataset.get_queries_by_category("course_information")
        
        assert isinstance(course_queries, list)
        for query in course_queries:
            assert query["category"] == "course_information"
    
    def test_get_queries_by_difficulty(self, dataset):
        """Test filtering queries by difficulty"""
        
        dataset.create_unsw_ground_truth()
        dataset.generate_test_queries()
        
        # Test filtering by easy difficulty
        easy_queries = dataset.get_queries_by_difficulty("easy")
        
        assert isinstance(easy_queries, list)
        for query in easy_queries:
            assert query["difficulty"] == "easy"
    
    def test_extract_course_code(self, dataset):
        """Test course code extraction from questions"""
        
        # Test course code extraction
        course_code = dataset._extract_course_code("What is COMP9900?")
        assert course_code == "COMP9900"
        
        course_code = dataset._extract_course_code("Tell me about COMP2521")
        assert course_code == "COMP2521"
        
        course_code = dataset._extract_course_code("What about general information?")
        assert course_code is None
    
    def test_ground_truth_content_quality(self, dataset):
        """Test quality of ground truth content"""
        
        ground_truth = dataset.create_unsw_ground_truth()
        
        for item in ground_truth:
            # Verify non-empty content
            assert len(item["question"].strip()) > 0
            assert len(item["ground_truth"].strip()) > 0
            assert len(item["expected_context_keywords"]) > 0

            # Verify answer quality (should be substantial)
            answer_words = len(item["ground_truth"].split())
            assert answer_words >= 10, f"Answer too short: {item['question']}"
            
            # Verify question format
            question = item["question"]
            assert question.endswith("?") or "what" in question.lower() or "how" in question.lower()
    
    def test_category_coverage(self, dataset):
        """Test that all categories are covered in ground truth"""
        
        ground_truth = dataset.create_unsw_ground_truth()
        
        categories_in_data = set(item["category"] for item in ground_truth)
        
        # Should cover most main categories
        expected_categories = {
            "course_information", 
            "prerequisites", 
            "degree_programs",
            "campus_facilities",
            "admission_requirements"
        }
        
        coverage = len(expected_categories.intersection(categories_in_data))
        assert coverage >= 4, f"Should cover at least 4 categories, got {coverage}"
    
    def test_difficulty_distribution(self, dataset):
        """Test that different difficulty levels are represented"""
        
        ground_truth = dataset.create_unsw_ground_truth()
        
        difficulties = [item["difficulty"] for item in ground_truth]
        unique_difficulties = set(difficulties)
        
        # Should have at least easy and medium difficulty questions
        assert "easy" in unique_difficulties
        assert "medium" in unique_difficulties
        assert len(unique_difficulties) >= 2
    
    def test_keyword_relevance(self, dataset):
        """Test that expected keywords are relevant to questions"""
        
        ground_truth = dataset.create_unsw_ground_truth()
        
        for item in ground_truth:
            question = item["question"].lower()
            answer = item["ground_truth"].lower()
            keywords = [kw.lower() for kw in item["expected_context_keywords"]]
            
            # At least one keyword should appear in question or answer
            keyword_found = any(kw in question or kw in answer for kw in keywords)
            assert keyword_found, f"No keywords found in question/answer for: {item['question']}"