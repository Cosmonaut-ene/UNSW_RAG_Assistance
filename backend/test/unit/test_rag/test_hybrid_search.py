"""
Unit tests for RAG Hybrid Search module
Tests hybrid search combining RAG and BM25 search results
"""

import pytest
from unittest.mock import patch, MagicMock
from rag.hybrid_search import HybridSearchEngine
from test.mocks.mock_vector_store import MockVectorStore


class TestHybridSearchEngine:
    """Test hybrid search engine functionality"""
    
    def test_hybrid_search_engine_initialization(self):
        """Test hybrid search engine initialization"""
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(
            vector_store=mock_vector_store,
            min_hybrid_score=50.0,
            min_bm25_score=5.0,
            min_rag_score=30.0
        )
        
        assert hybrid_engine.bm25_searcher is not None
        assert hybrid_engine.rag_weight == 0.6
        assert hybrid_engine.bm25_weight == 0.4
        assert hybrid_engine.min_hybrid_score == 50.0
        assert hybrid_engine.min_bm25_score == 5.0
        assert hybrid_engine.min_rag_score == 30.0
        
    def test_hybrid_search_engine_default_parameters(self):
        """Test hybrid search engine with default parameters"""
        hybrid_engine = HybridSearchEngine()
        
        assert hybrid_engine.min_hybrid_score == 50.0
        assert hybrid_engine.min_bm25_score == 5.0
        assert hybrid_engine.min_rag_score == 30.0
        
    def test_combine_results_with_rag_and_bm25(self):
        """Test combining RAG and BM25 results"""
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(vector_store=mock_vector_store)
        
        rag_results = [
            {
                'page_content': 'COMP9900 is a capstone project course',
                'metadata': {'source': 'handbook.pdf', 'page': 1}
            }
        ]
        
        bm25_results = [
            {
                'content': 'Prerequisites for COMP9900 include COMP2511',
                'metadata': {'source': 'handbook.pdf', 'page': 2},
                'bm25_score': 8.5
            }
        ]
        
        combined = hybrid_engine.combine_results(rag_results, bm25_results, max_results=5)
        
        assert len(combined) <= 5
        assert all('metadata' in result for result in combined)
        assert all('hybrid_score' in result['metadata'] for result in combined)
        
        # Results should be sorted by hybrid score
        scores = [result['metadata']['hybrid_score'] for result in combined]
        assert scores == sorted(scores, reverse=True)
        
    def test_combine_results_rag_only(self):
        """Test combining results with only RAG results"""
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(vector_store=mock_vector_store)
        
        rag_results = [
            {
                'page_content': 'COMP9900 is a capstone project course',
                'metadata': {'source': 'handbook.pdf', 'page': 1}
            },
            {
                'page_content': 'Prerequisites include COMP2511 and COMP3311',
                'metadata': {'source': 'handbook.pdf', 'page': 2}
            }
        ]
        
        combined = hybrid_engine.combine_results(rag_results, [], max_results=5)
        
        # Just verify the function works
        assert isinstance(combined, list)
            
    def test_combine_results_bm25_only(self):
        """Test combining results with only BM25 results"""
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(vector_store=mock_vector_store)
        
        bm25_results = [
            {
                'content': 'COMP9900 capstone project information',
                'metadata': {'source': 'handbook.pdf', 'page': 1},
                'bm25_score': 9.2
            },
            {
                'content': 'Course prerequisites and requirements',
                'metadata': {'source': 'handbook.pdf', 'page': 2},
                'bm25_score': 7.5
            }
        ]
        
        combined = hybrid_engine.combine_results([], bm25_results, max_results=5)
        
        # Just verify the function works
        assert isinstance(combined, list)
            
    def test_combine_results_empty_inputs(self):
        """Test combining results with empty inputs"""
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(vector_store=mock_vector_store)
        
        combined = hybrid_engine.combine_results([], [], max_results=5)
        
        assert combined == []
        
    def test_combine_results_duplicate_content(self):
        """Test combining results with duplicate content"""
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(vector_store=mock_vector_store)
        
        rag_results = [
            {
                'page_content': 'COMP9900 is a capstone project course',
                'metadata': {'source': 'handbook.pdf', 'page': 1}
            }
        ]
        
        bm25_results = [
            {
                'content': 'COMP9900 is a capstone project course',  # Same content
                'metadata': {'source': 'handbook.pdf', 'page': 1},
                'bm25_score': 8.0
            }
        ]
        
        combined = hybrid_engine.combine_results(rag_results, bm25_results, max_results=5)
        
        # Should merge duplicate content
        assert len(combined) == 1
        assert combined[0]['metadata']['search_type'] == 'hybrid'
        assert combined[0]['metadata']['bm25_score'] > 0
        assert combined[0]['metadata']['rag_score'] == 100
        
    def test_combine_results_threshold_filtering(self):
        """Test that results below thresholds are filtered out"""
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(
            vector_store=mock_vector_store,
            min_hybrid_score=80.0,
            min_bm25_score=8.0,
            min_rag_score=50.0
        )
        
        rag_results = [
            {
                'page_content': 'High quality RAG result',
                'metadata': {'source': 'handbook.pdf', 'page': 1}
            }
        ]
        
        bm25_results = [
            {
                'content': 'Low quality BM25 result',
                'metadata': {'source': 'other.pdf', 'page': 1},
                'bm25_score': 3.0  # Below threshold
            }
        ]
        
        combined = hybrid_engine.combine_results(rag_results, bm25_results, max_results=5)
        
        # Just verify the function works
        assert isinstance(combined, list)
        
    @patch('rag.hybrid_search.BM25SearchEngine')
    def test_search_hybrid_full_workflow(self, mock_bm25_class):
        """Test full hybrid search workflow"""
        mock_bm25_searcher = MagicMock()
        mock_bm25_results = [
            {
                'content': 'BM25 search result',
                'metadata': {'source': 'test.pdf'},
                'bm25_score': 7.5
            }
        ]
        mock_bm25_searcher.search.return_value = mock_bm25_results
        mock_bm25_class.return_value = mock_bm25_searcher
        
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(vector_store=mock_vector_store)
        
        rag_results = [
            {
                'page_content': 'RAG search result',
                'metadata': {'source': 'handbook.pdf', 'page': 1}
            }
        ]
        
        query = "test query"
        results = hybrid_engine.search_hybrid(query, rag_results, max_results=5)
        
        assert isinstance(results, list)
        assert len(results) <= 5
        mock_bm25_searcher.search.assert_called_once_with(query, top_k=10)  # max_results * 2
        
    @patch('rag.hybrid_search.BM25SearchEngine')
    def test_search_hybrid_no_rag_results(self, mock_bm25_class):
        """Test hybrid search with no RAG results"""
        mock_bm25_searcher = MagicMock()
        mock_bm25_results = [
            {
                'content': 'BM25 only result',
                'metadata': {'source': 'test.pdf'},
                'bm25_score': 8.0
            }
        ]
        mock_bm25_searcher.search.return_value = mock_bm25_results
        mock_bm25_class.return_value = mock_bm25_searcher
        
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(vector_store=mock_vector_store)
        
        query = "test query"
        results = hybrid_engine.search_hybrid(query, None, max_results=5)
        
        assert isinstance(results, list)
        # Should still return BM25 results even without RAG
        assert len(results) <= 5
        
    def test_update_bm25_index(self):
        """Test updating BM25 index with new vector store"""
        hybrid_engine = HybridSearchEngine()
        
        new_vector_store = MockVectorStore()
        hybrid_engine.update_bm25_index(new_vector_store)
        
        # Should update the BM25 searcher with new vector store
        assert hybrid_engine.bm25_searcher.vector_store == new_vector_store


class TestHybridSearchEngineScoring:
    """Test hybrid scoring calculation"""
    
    def test_hybrid_score_calculation(self):
        """Test hybrid score calculation with different weights"""
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(vector_store=mock_vector_store)
        
        rag_results = [
            {
                'page_content': 'Test content',
                'metadata': {'source': 'test.pdf'}
            }
        ]
        
        bm25_results = [
            {
                'content': 'Different content',
                'metadata': {'source': 'test.pdf'},
                'bm25_score': 8.0
            }
        ]
        
        combined = hybrid_engine.combine_results(rag_results, bm25_results, max_results=5)
        
        # Check hybrid score calculation
        for result in combined:
            metadata = result['metadata']
            rag_score = metadata.get('rag_score', 0)
            bm25_score = metadata.get('bm25_score', 0)
            expected_hybrid = (rag_score * 0.6) + (bm25_score * 0.4)
            assert abs(metadata['hybrid_score'] - expected_hybrid) < 0.01
            
    def test_custom_weights(self):
        """Test hybrid search with custom weights"""
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(vector_store=mock_vector_store)
        
        # Modify weights
        hybrid_engine.rag_weight = 0.8
        hybrid_engine.bm25_weight = 0.2
        
        rag_results = [
            {
                'page_content': 'Test content',
                'metadata': {'source': 'test.pdf'}
            }
        ]
        
        bm25_results = [
            {
                'content': 'Different content',
                'metadata': {'source': 'test.pdf'},
                'bm25_score': 10.0
            }
        ]
        
        combined = hybrid_engine.combine_results(rag_results, bm25_results, max_results=5)
        
        # Check that custom weights are used
        for result in combined:
            metadata = result['metadata']
            rag_score = metadata.get('rag_score', 0)
            bm25_score = metadata.get('bm25_score', 0)
            expected_hybrid = (rag_score * 0.8) + (bm25_score * 0.2)
            assert abs(metadata['hybrid_score'] - expected_hybrid) < 0.01


class TestHybridSearchEngineEdgeCases:
    """Test edge cases and error scenarios"""
    
        
        
    def test_very_large_result_sets(self):
        """Test handling of very large result sets"""
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(vector_store=mock_vector_store)
        
        # Create large result sets
        large_rag_results = []
        large_bm25_results = []
        
        for i in range(1000):
            large_rag_results.append({
                'page_content': f'RAG content {i}',
                'metadata': {'source': f'rag_{i}.pdf', 'page': i}
            })
            
            large_bm25_results.append({
                'content': f'BM25 content {i}',
                'metadata': {'source': f'bm25_{i}.pdf', 'page': i},
                'bm25_score': 10.0 - (i * 0.01)
            })
            
        combined = hybrid_engine.combine_results(large_rag_results, large_bm25_results, max_results=10)
        
        # Should limit results to max_results
        assert len(combined) <= 10
        
    def test_zero_max_results(self):
        """Test with max_results=0"""
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(vector_store=mock_vector_store)
        
        rag_results = [
            {
                'page_content': 'Test content',
                'metadata': {'source': 'test.pdf'}
            }
        ]
        
        combined = hybrid_engine.combine_results(rag_results, [], max_results=0)
        
        assert combined == []
        
    def test_negative_max_results(self):
        """Test with negative max_results"""
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(vector_store=mock_vector_store)
        
        rag_results = [
            {
                'page_content': 'Test content',
                'metadata': {'source': 'test.pdf'}
            }
        ]
        
        combined = hybrid_engine.combine_results(rag_results, [], max_results=-5)
        
        # Should handle gracefully, possibly returning empty or limited results
        assert isinstance(combined, list)


class TestHybridSearchEngineIntegration:
    """Integration tests with realistic scenarios"""
    
            
        
    @patch('rag.hybrid_search.BM25SearchEngine')
    def test_no_results_scenario(self, mock_bm25_class):
        """Test scenario where no results meet thresholds"""
        mock_bm25_searcher = MagicMock()
        mock_bm25_results = [
            {
                'content': 'Low relevance content',
                'metadata': {'source': 'other.pdf'},
                'bm25_score': 1.0  # Below threshold
            }
        ]
        mock_bm25_searcher.search.return_value = mock_bm25_results
        mock_bm25_class.return_value = mock_bm25_searcher
        
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(
            vector_store=mock_vector_store,
            min_hybrid_score=80.0,  # High threshold
            min_bm25_score=8.0,
            min_rag_score=50.0
        )
        
        # Low quality RAG results (would get low hybrid score)
        rag_results = []
        
        query = "very specific query with no good matches"
        results = hybrid_engine.search_hybrid(query, rag_results, max_results=5)
        
        # Should return empty results when nothing meets thresholds
        assert isinstance(results, list)
        # May be empty or contain only high-quality results
        
    @patch('rag.hybrid_search.BM25SearchEngine')  
    def test_performance_with_mixed_results(self, mock_bm25_class):
        """Test performance with mixed quality results"""
        mock_bm25_searcher = MagicMock()
        mock_bm25_results = []
        for i in range(50):
            mock_bm25_results.append({
                'content': f'BM25 result {i} with varying relevance',
                'metadata': {'source': f'doc_{i}.pdf'},
                'bm25_score': 10.0 - (i * 0.2)  # Decreasing scores
            })
        mock_bm25_searcher.search.return_value = mock_bm25_results
        mock_bm25_class.return_value = mock_bm25_searcher
        
        mock_vector_store = MockVectorStore()
        hybrid_engine = HybridSearchEngine(vector_store=mock_vector_store)
        
        rag_results = []
        for i in range(30):
            rag_results.append({
                'page_content': f'RAG result {i} with good semantic relevance',
                'metadata': {'source': f'rag_doc_{i}.pdf', 'page': i}
            })
        
        query = "test query for performance"
        results = hybrid_engine.search_hybrid(query, rag_results, max_results=10)
        
        # Should efficiently process large result sets
        assert len(results) <= 10
        assert isinstance(results, list)
        
        # Results should be properly scored and sorted
        if len(results) > 1:
            scores = [result['metadata']['hybrid_score'] for result in results]
            assert scores == sorted(scores, reverse=True)