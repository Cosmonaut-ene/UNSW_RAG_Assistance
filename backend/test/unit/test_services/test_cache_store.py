"""
Unit tests for services/cache_store.py

Focused on the fuzzy-match course-code collision fix: two questions
differing only in which course they name (e.g. "...without COMP2521?" vs
"...without COMP2511?") can score above the 0.95 SequenceMatcher
threshold purely because the rest of the sentence is identical, which
would silently return the wrong course's cached answer.
"""

from unittest.mock import patch

from services.cache_store import (
    extract_course_codes,
    find_cached_answer,
    similarity,
)


class TestExtractCourseCodes:

    def test_extracts_single_code(self):
        assert extract_course_codes("What is COMP1511?") == {"COMP1511"}

    def test_extracts_multiple_codes(self):
        assert extract_course_codes("Can I take COMP3311 without COMP2521?") == {"COMP3311", "COMP2521"}

    def test_case_insensitive(self):
        assert extract_course_codes("what is comp1511?") == {"COMP1511"}

    def test_no_codes_returns_empty_set(self):
        assert extract_course_codes("Where is the library?") == set()

    def test_non_comp_prefixes(self):
        assert extract_course_codes("What is MATH1081 and SENG2011?") == {"MATH1081", "SENG2011"}


class TestFindCachedAnswerSimilarityMatch:

    @patch('services.cache_store.save_all_cache_entries')
    @patch('services.cache_store.load_all_cache_entries')
    def test_similarity_match_rejected_when_course_codes_differ(self, mock_load, mock_save):
        """
        The bug: 'can i take comp3311 without comp2521?' vs '...comp2511?'
        scores ~0.97 on SequenceMatcher despite naming a different course.
        Must not return the wrong course's cached answer.
        """
        mock_load.return_value = [{
            "question_hash": "abc123",
            "question": "Can I take COMP3311 without COMP2521?",
            "answer": "Yes, COMP2521 is required before COMP3311.",
            "usage_count": 1,
        }]

        answer, found, entry = find_cached_answer("Can I take COMP3311 without COMP2511?")

        assert found is False
        assert answer is None
        mock_save.assert_not_called()

    @patch('services.cache_store.save_all_cache_entries')
    @patch('services.cache_store.load_all_cache_entries')
    def test_similarity_match_still_works_for_same_course_paraphrase(self, mock_load, mock_save):
        """The fix must not break genuine near-duplicate matching for the same course"""
        mock_load.return_value = [{
            "question_hash": "abc123",
            "question": "What is COMP1511 about?",
            "answer": "COMP1511 is Programming Fundamentals.",
            "usage_count": 1,
        }]

        answer, found, entry = find_cached_answer("What is COMP1511 about?!")

        assert found is True
        assert answer == "COMP1511 is Programming Fundamentals."

    @patch('services.cache_store.save_all_cache_entries')
    @patch('services.cache_store.load_all_cache_entries')
    def test_similarity_match_works_when_neither_question_names_a_course(self, mock_load, mock_save):
        mock_load.return_value = [{
            "question_hash": "abc123",
            "question": "Where can I find the CSE computer labs on campus?",
            "answer": "In the K17 building.",
            "usage_count": 1,
        }]

        answer, found, entry = find_cached_answer("Where can I find the CSE computer labs on campus")

        assert found is True
        assert answer == "In the K17 building."

    @patch('services.cache_store.save_all_cache_entries')
    @patch('services.cache_store.load_all_cache_entries')
    def test_exact_hash_match_takes_priority_over_similarity(self, mock_load, mock_save):
        mock_load.return_value = [{
            "question_hash": "e3b0c44298fc1c14",  # not a real computed hash, just distinct
            "question": "what is comp1511?",
            "answer": "exact match answer",
            "usage_count": 1,
        }]

        with patch('services.cache_store.get_question_hash', return_value="e3b0c44298fc1c14"):
            answer, found, entry = find_cached_answer("what is comp1511?")

        assert found is True
        assert answer == "exact match answer"

    @patch('services.cache_store.save_all_cache_entries')
    @patch('services.cache_store.load_all_cache_entries')
    def test_no_match_returns_none(self, mock_load, mock_save):
        mock_load.return_value = []

        answer, found, entry = find_cached_answer("What is COMP1511?")

        assert found is False
        assert answer is None
        assert entry is None


class TestSimilarity:

    def test_identical_strings(self):
        assert similarity("hello", "hello") == 1.0

    def test_confirms_the_collision_that_motivated_this_fix(self):
        """
        Documents the exact bug: SequenceMatcher alone scores this pair
        above the 0.95 threshold even though COMP2521 != COMP2511.
        extract_course_codes() is what actually prevents the false match
        (see TestFindCachedAnswerSimilarityMatch above).
        """
        score = similarity(
            "can i take comp3311 without comp2521?",
            "can i take comp3311 without comp2511?",
        )
        assert score > 0.95
