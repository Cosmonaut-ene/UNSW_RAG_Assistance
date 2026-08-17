"""
Unit tests for RAG HyDE (Hypothetical Document Embeddings) module
"""

from unittest.mock import MagicMock, patch

from rag.hyde import hyde_search, generate_hypothetical_document


class FakeDoc:
    """Minimal stand-in for a langchain Document"""

    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


class TestHydeSearch:
    """Test hyde_search only searches the hypothetical document, not the original query"""

    def test_hyde_search_calls_search_fn_exactly_once(self):
        """hyde_search must not also search the original query (that's retrieve_node's job)"""
        search_fn = MagicMock(return_value=[FakeDoc("some content")])

        hyde_search("a hypothetical answer", search_fn, k=10)

        assert search_fn.call_count == 1

    def test_hyde_search_queries_with_hyde_doc_not_original_query(self):
        """The single search call must use the hyde_doc text, not any original query"""
        search_fn = MagicMock(return_value=[])

        hyde_search("hypothetical doc text", search_fn, k=10)

        called_args, called_kwargs = search_fn.call_args
        assert called_args[0] == "hypothetical doc text"
        assert called_kwargs.get("k") == 10

    def test_hyde_search_deduplicates_by_content_prefix(self):
        """Results with the same first-150-char prefix are deduplicated"""
        duplicate_content = "x" * 200
        search_fn = MagicMock(return_value=[
            FakeDoc(duplicate_content),
            FakeDoc(duplicate_content),
            FakeDoc("a distinct chunk"),
        ])

        results = hyde_search("hypothetical doc text", search_fn, k=10)

        assert len(results) == 2

    def test_hyde_search_empty_results(self):
        """No results from search_fn returns an empty list without error"""
        search_fn = MagicMock(return_value=[])

        results = hyde_search("hypothetical doc text", search_fn, k=10)

        assert results == []


class TestGenerateHypotheticalDocumentPrompt:
    """
    The prompt must not ask the model to invent specific course codes --
    a fabricated code would pull embedding-based retrieval toward an
    unrelated course instead of helping it (see A3 in SPEC.md).
    """

    @patch('ai.llm_client.get_genai_model')
    def test_prompt_does_not_ask_for_course_codes(self, mock_get_model):
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "A hypothetical answer."
        mock_get_model.return_value = mock_model

        generate_hypothetical_document("What is COMP9900?")

        prompt_sent = mock_model.generate_content.call_args[0][0]
        assert "course codes" not in prompt_sent.lower() or "do not invent" in prompt_sent.lower()
        assert "contain specific details, course codes" not in prompt_sent

    @patch('ai.llm_client.get_genai_model')
    def test_prompt_explicitly_forbids_inventing_identifiers(self, mock_get_model):
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "A hypothetical answer."
        mock_get_model.return_value = mock_model

        generate_hypothetical_document("What is COMP9900?")

        prompt_sent = mock_model.generate_content.call_args[0][0]
        assert "do not invent" in prompt_sent.lower() or "not invent" in prompt_sent.lower()

    @patch('ai.llm_client.get_genai_model')
    def test_prompt_still_asks_for_document_style_language(self, mock_get_model):
        """The style-matching instruction (HyDE's actual purpose) must remain"""
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "A hypothetical answer."
        mock_get_model.return_value = mock_model

        generate_hypothetical_document("What is COMP9900?")

        prompt_sent = mock_model.generate_content.call_args[0][0]
        assert "unsw documentation" in prompt_sent.lower()
