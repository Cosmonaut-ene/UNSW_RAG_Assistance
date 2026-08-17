"""
Unit tests for rag/search_engine.py -- similarity score normalization (B1)
"""

from rag.search_engine import normalize_similarity_score


class TestNormalizeSimilarityScore:
    """
    Chroma's similarity_search_with_score returns L2 distance (lower = more
    similar). Embeddings are unit-normalized, so distance ranges [0, 2] for
    unit vectors; this converts that into a 0-100 "higher is better" score
    on the same scale BM25 scores are normalized to.
    """

    def test_zero_distance_is_perfect_score(self):
        assert normalize_similarity_score(0.0) == 100.0

    def test_max_distance_is_zero_score(self):
        assert normalize_similarity_score(2.0) == 0.0

    def test_mid_distance_is_mid_score(self):
        assert normalize_similarity_score(1.0) == 50.0

    def test_distance_beyond_max_clamped_to_zero(self):
        assert normalize_similarity_score(4.0) == 0.0

    def test_negative_distance_clamped_to_hundred(self):
        # Shouldn't happen in practice, but must never exceed 100
        assert normalize_similarity_score(-1.0) == 100.0

    def test_score_always_in_valid_range(self):
        for distance in [0.0, 0.3, 0.7, 1.2, 1.9, 2.0, 3.0]:
            score = normalize_similarity_score(distance)
            assert 0.0 <= score <= 100.0

    def test_lower_distance_always_yields_higher_score(self):
        assert normalize_similarity_score(0.2) > normalize_similarity_score(0.8)
