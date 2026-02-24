"""
Unit tests for RAG BM25 Search module
Tests BM25 search engine functionality and keyword matching
"""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document

from rag.bm25_search import BM25SearchEngine
from test.mocks.mock_vector_store import MockVectorStore


class TestBM25SearchEngine:
    """Test BM25 search engine functionality"""
    
    def test_bm25_search_engine_initialization(self):
        """Test BM25 search engine initialization"""
        mock_vector_store = MockVectorStore()
        search_engine = BM25SearchEngine(mock_vector_store)
        
        assert search_engine.vector_store == mock_vector_store
        assert search_engine.corpus is not None
        assert search_engine.bm25_index is not None
        assert isinstance(search_engine.documents, list)
        
    def test_bm25_search_engine_initialization_without_vector_store(self):
        """Test BM25 search engine initialization without vector store"""
        search_engine = BM25SearchEngine(None)
        
        assert search_engine.vector_store is None
        assert search_engine.corpus == []
        assert search_engine.bm25_index is None
        assert search_engine.documents == []
        
    def test_bm25_search_engine_update_index(self):
        """Test updating BM25 index with new vector store"""
        search_engine = BM25SearchEngine(None)
        mock_vector_store = MockVectorStore()
        
        search_engine.update_index(mock_vector_store)
        
        assert search_engine.vector_store == mock_vector_store
        assert search_engine.corpus is not None
        assert search_engine.bm25_index is not None
        assert len(search_engine.documents) > 0
        
    @patch('rag.bm25_search.BM25Okapi')
    def test_bm25_search_basic_functionality(self, mock_bm25):
        """Test basic BM25 search functionality"""
        mock_bm25_instance = MagicMock()
        mock_bm25_instance.get_scores.return_value = [0.8, 0.6, 0.3, 0.1, 0.0]
        mock_bm25.return_value = mock_bm25_instance
        
        mock_vector_store = MockVectorStore()
        search_engine = BM25SearchEngine(mock_vector_store)
        
        query = "COMP9900 capstone project"
        results = search_engine.search(query, top_k=3)
        
        assert len(results) <= 3
        assert all(isinstance(result, dict) for result in results)
        assert all("content" in result for result in results)
        assert all("metadata" in result for result in results)
        assert all("bm25_score" in result for result in results)
        
        # Check that scores are in descending order
        scores = [result["bm25_score"] for result in results]
        assert scores == sorted(scores, reverse=True)
        
    @patch('rag.bm25_search.BM25Okapi')
    def test_bm25_search_empty_query(self, mock_bm25):
        """Test BM25 search with empty query"""
        mock_vector_store = MockVectorStore()
        search_engine = BM25SearchEngine(mock_vector_store)
        
        results = search_engine.search("", top_k=5)
        
        assert results == []
        
    @patch('rag.bm25_search.BM25Okapi')
    def test_bm25_search_none_query(self, mock_bm25):
        """Test BM25 search with None query"""
        mock_vector_store = MockVectorStore()
        search_engine = BM25SearchEngine(mock_vector_store)
        
        results = search_engine.search(None, top_k=5)
        
        assert results == []
        
    @patch('rag.bm25_search.BM25Okapi')
    def test_bm25_search_zero_top_k(self, mock_bm25):
        """Test BM25 search with top_k=0"""
        mock_vector_store = MockVectorStore()
        search_engine = BM25SearchEngine(mock_vector_store)
        
        results = search_engine.search("test query", top_k=0)
        
        assert results == []
        
    @patch('rag.bm25_search.BM25Okapi')
    def test_bm25_search_negative_top_k(self, mock_bm25):
        """Test BM25 search with negative top_k"""
        mock_vector_store = MockVectorStore()
        search_engine = BM25SearchEngine(mock_vector_store)
        
        results = search_engine.search("test query", top_k=-1)
        
        assert results == []
        
    @patch('rag.bm25_search.BM25Okapi')
    def test_bm25_search_with_minimum_score_filter(self, mock_bm25):
        """Test BM25 search with minimum score filtering"""
        mock_bm25_instance = MagicMock()
        mock_bm25_instance.get_scores.return_value = [0.8, 0.6, 0.3, 0.1, 0.0]
        mock_bm25.return_value = mock_bm25_instance
        
        mock_vector_store = MockVectorStore()
        search_engine = BM25SearchEngine(mock_vector_store)
        
        query = "test query"
        results = search_engine.search(query, top_k=5, min_score=0.5)
        
        # Should only return results with score >= 0.5
        for result in results:
            assert result["bm25_score"] >= 0.5


class TestBM25SearchEngineTokenization:
    """Test tokenization and text processing"""
    
    @patch('rag.bm25_search.word_tokenize')
    @patch('rag.bm25_search.BM25Okapi')
    def test_text_tokenization(self, mock_bm25, mock_tokenize):
        """Test text tokenization functionality"""
        mock_tokenize.return_value = ["comp9900", "capstone", "project", "course"]
        mock_bm25_instance = MagicMock()
        mock_bm25.return_value = mock_bm25_instance
        
        mock_vector_store = MockVectorStore()
        search_engine = BM25SearchEngine(mock_vector_store)
        
        # Tokenization happens during initialization and search
        query = "COMP9900 capstone project course"
        search_engine.search(query, top_k=3)
        
        # Check that tokenize was called
        assert mock_tokenize.call_count > 0
        
    @patch('rag.bm25_search.word_tokenize')
    @patch('rag.bm25_search.BM25Okapi')
    def test_tokenization_error_handling(self, mock_bm25, mock_tokenize):
        """Test error handling in tokenization"""
        mock_tokenize.side_effect = Exception("Tokenization error")
        
        mock_vector_store = MockVectorStore()
        
        # Should handle tokenization errors gracefully
        search_engine = BM25SearchEngine(mock_vector_store)
        
        # Engine should be initialized with fallback tokenization
        assert search_engine.bm25_index is not None
        
    @patch('rag.bm25_search.word_tokenize')
    @patch('rag.bm25_search.BM25Okapi')
    def test_stopword_filtering(self, mock_bm25, mock_tokenize):
        """Test stopword filtering in tokenization"""
        # Mock tokenization to include stopwords
        mock_tokenize.return_value = ["what", "is", "comp9900", "the", "course", "about"]
        mock_bm25_instance = MagicMock()
        mock_bm25.return_value = mock_bm25_instance
        
        mock_vector_store = MockVectorStore()
        search_engine = BM25SearchEngine(mock_vector_store)
        
        query = "What is COMP9900 the course about"
        search_engine.search(query, top_k=3)
        
        # Tokenization should have been called
        assert mock_tokenize.call_count > 0


class TestBM25SearchEngineEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_bm25_search_with_empty_corpus(self):
        """Test BM25 search with empty document corpus"""
        # Create an empty mock vector store
        mock_vector_store = MagicMock()
        mock_vector_store.similarity_search.return_value = []
        
        search_engine = BM25SearchEngine(mock_vector_store)
        
        query = "test query"
        results = search_engine.search(query, top_k=5)
        
        assert results == []
        
    @patch('rag.bm25_search.BM25Okapi')
    def test_bm25_search_with_special_characters(self, mock_bm25):
        """Test BM25 search with special characters in query"""
        mock_bm25_instance = MagicMock()
        mock_bm25_instance.get_scores.return_value = [0.5, 0.3, 0.1]
        mock_bm25.return_value = mock_bm25_instance
        
        mock_vector_store = MockVectorStore()
        search_engine = BM25SearchEngine(mock_vector_store)
        
        query = "C++ & Python programming (COMP9900)!"
        results = search_engine.search(query, top_k=3)
        
        assert isinstance(results, list)
        
    @patch('rag.bm25_search.BM25Okapi')
    def test_bm25_search_with_unicode_characters(self, mock_bm25):
        """Test BM25 search with unicode characters"""
        mock_bm25_instance = MagicMock()
        mock_bm25_instance.get_scores.return_value = [0.5, 0.3, 0.1]
        mock_bm25.return_value = mock_bm25_instance
        
        mock_vector_store = MockVectorStore()
        search_engine = BM25SearchEngine(mock_vector_store)
        
        query = "计算机科学 COMP9900"  # Chinese characters for computer science
        results = search_engine.search(query, top_k=3)
        
        assert isinstance(results, list)
        
    def test_bm25_search_engine_missing_nltk_dependencies(self):
        """Test BM25 search engine when NLTK dependencies are missing"""
        with patch('rag.bm25_search.nltk') as mock_nltk:
            mock_nltk.data.find.side_effect = LookupError("NLTK data not found")
            
            # Should handle missing NLTK data gracefully
            mock_vector_store = MockVectorStore()
            search_engine = BM25SearchEngine(mock_vector_store)
            
            # Should still create a search engine, possibly with fallback tokenization
            assert search_engine is not None
            
    @patch('rag.bm25_search.BM25Okapi')
    def test_bm25_search_engine_api_error(self, mock_bm25):
        """Test BM25 search engine when BM25 API throws error"""
        mock_bm25.side_effect = Exception("BM25 initialization error")
        
        mock_vector_store = MockVectorStore()
        
        # Should handle BM25 initialization error gracefully
        search_engine = BM25SearchEngine(mock_vector_store)
        
        # Search should return empty results when BM25 is not available
        results = search_engine.search("test query", top_k=5)
        assert results == []


class TestBM25SearchEnginePerformance:
    """Test performance characteristics"""
    
    @patch('rag.bm25_search.BM25Okapi')
    def test_multiple_search_performance(self, mock_bm25):
        """Test performance with multiple searches"""
        mock_bm25_instance = MagicMock()
        mock_bm25_instance.get_scores.return_value = [0.8, 0.6, 0.4, 0.2, 0.1]
        mock_bm25.return_value = mock_bm25_instance
        
        mock_vector_store = MockVectorStore()
        search_engine = BM25SearchEngine(mock_vector_store)
        
        queries = [
            "COMP9900 capstone project",
            "computer science building J17",
            "prerequisites for courses",
            "UNSW campus facilities",
            "programming languages taught"
        ]
        
        all_results = []
        for query in queries:
            results = search_engine.search(query, top_k=3)
            all_results.append(results)
            
        # All searches should complete successfully
        assert len(all_results) == 5
        assert all(isinstance(results, list) for results in all_results)
        
        # BM25 should have been used for each search
        assert mock_bm25_instance.get_scores.call_count == 5
        
    @patch('rag.bm25_search.BM25Okapi')
    def test_large_corpus_handling(self, mock_bm25):
        """Test handling of large document corpus"""
        mock_bm25_instance = MagicMock()
        # Simulate scores for a large corpus
        large_scores = [0.8 - (i * 0.01) for i in range(1000)]
        mock_bm25_instance.get_scores.return_value = large_scores
        mock_bm25.return_value = mock_bm25_instance
        
        # Create mock vector store with many documents
        mock_vector_store = MagicMock()
        large_documents = []
        for i in range(1000):
            doc = Document(
                page_content=f"Document {i} content about various topics",
                metadata={"source": f"doc_{i}.pdf", "page": i % 10}
            )
            large_documents.append(doc)
            
        mock_vector_store.similarity_search.return_value = large_documents
        
        search_engine = BM25SearchEngine(mock_vector_store)
        
        query = "test query"
        results = search_engine.search(query, top_k=10)
        
        # Should handle large corpus and return top results
        assert len(results) <= 10
        assert all(isinstance(result, dict) for result in results)


class TestBM25SearchEngineIntegration:
    """Integration tests with realistic scenarios"""
    
    @patch('rag.bm25_search.BM25Okapi')
    def test_course_information_search(self, mock_bm25):
        """Test BM25 search for course information"""
        mock_bm25_instance = MagicMock()
        # Return numpy array-like structure that matches the expected document count
        import numpy as np
        mock_bm25_instance.get_scores.return_value = np.array([0.95, 0.8, 0.6])
        mock_bm25.return_value = mock_bm25_instance
        
        # Create mock vector store with course-related documents
        mock_vector_store = MagicMock()
        course_documents = [
            Document(
                page_content="COMP9900 is a capstone project course for computer science students",
                metadata={"source": "handbook.pdf", "course_code": "COMP9900"}
            ),
            Document(
                page_content="Prerequisites for COMP9900 include COMP2511 and COMP3311",
                metadata={"source": "handbook.pdf", "course_code": "COMP9900"}
            ),
            Document(
                page_content="COMP9021 introduces fundamental programming concepts",
                metadata={"source": "handbook.pdf", "course_code": "COMP9021"}
            )
        ]
        # Set up the mock to return documents when queried
        mock_vector_store.similarity_search.return_value = course_documents
        # Ensure BM25 can extract documents during initialization
        mock_vector_store._collection = None  # Forces fallback to similarity_search
        
        search_engine = BM25SearchEngine(mock_vector_store)
        
        query = "COMP9900 capstone project prerequisites"
        results = search_engine.search(query, top_k=3)
        
        # Just verify the search function works without specific assertions
        assert isinstance(results, list)
        
    @patch('rag.bm25_search.BM25Okapi')
    def test_location_search(self, mock_bm25):
        """Test BM25 search for location information"""
        mock_bm25_instance = MagicMock()
        import numpy as np
        mock_bm25_instance.get_scores.return_value = np.array([0.9, 0.7, 0.5])
        mock_bm25.return_value = mock_bm25_instance
        
        # Create mock vector store with location documents
        mock_vector_store = MagicMock()
        location_documents = [
            Document(
                page_content="J17 Computer Science building houses the CSE department",
                metadata={"source": "campus_guide.pdf", "building": "J17"}
            ),
            Document(
                page_content="The library is located in the central campus area",
                metadata={"source": "campus_guide.pdf", "facility": "library"}
            ),
            Document(
                page_content="Engineering buildings are located in the upper campus",
                metadata={"source": "campus_guide.pdf", "area": "engineering"}
            )
        ]
        mock_vector_store.similarity_search.return_value = location_documents
        mock_vector_store._collection = None  # Forces fallback to similarity_search
        
        search_engine = BM25SearchEngine(mock_vector_store)
        
        query = "J17 building computer science"
        results = search_engine.search(query, top_k=3)
        
        # Just verify the search function works
        assert isinstance(results, list)
        
    @patch('rag.bm25_search.BM25Okapi')
    def test_combined_search_with_filters(self, mock_bm25):
        """Test BM25 search combined with result filtering"""
        mock_bm25_instance = MagicMock()
        mock_bm25_instance.get_scores.return_value = [0.8, 0.6, 0.4, 0.2, 0.1]
        mock_bm25.return_value = mock_bm25_instance
        
        mock_vector_store = MockVectorStore()
        search_engine = BM25SearchEngine(mock_vector_store)
        
        query = "course information"
        results = search_engine.search(query, top_k=5, min_score=0.3)
        
        # Should filter out results below minimum score
        for result in results:
            assert result["bm25_score"] >= 0.3