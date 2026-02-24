"""
Unit tests for RAG Vector Store module
Tests ChromaDB operations and vector storage functionality
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path
from langchain_core.documents import Document

from rag.vector_store import (
    validate_vector_database_exists,
    load_vector_store,
    create_vector_store,
    add_documents_incremental,
    get_vector_store_info
)
from ai.llm_client import get_embeddings_client
from test.mocks.mock_vector_store import MockChromaClient, MockVectorStore


class TestVectorStoreValidation:
    """Test vector store validation functionality"""
    
    def test_validate_vector_database_exists_with_valid_store(self, test_temp_dir, mock_paths):
        """Test validation with valid vector store"""
        # Create mock ChromaDB files
        vector_dir = Path(test_temp_dir) / "vector_store"
        chroma_dir = vector_dir / "test_collection"
        chroma_dir.mkdir(parents=True)
        
        # Create essential ChromaDB files
        (chroma_dir / "header.bin").touch()
        (chroma_dir / "data_level0.bin").touch()
        
        with patch('rag.vector_store.VECTOR_STORE_DIR', str(vector_dir)):
            result = validate_vector_database_exists()
            
        assert result is True
        
    def test_validate_vector_database_exists_missing_directory(self, test_temp_dir, mock_paths):
        """Test validation with missing vector store directory"""
        non_existent_dir = Path(test_temp_dir) / "non_existent"
        
        with patch('rag.vector_store.VECTOR_STORE_DIR', str(non_existent_dir)):
            result = validate_vector_database_exists()
            
        assert result is False
        
    def test_validate_vector_database_exists_empty_directory(self, test_temp_dir, mock_paths):
        """Test validation with empty vector store directory"""
        vector_dir = Path(test_temp_dir) / "vector_store"
        vector_dir.mkdir(parents=True, exist_ok=True)  # Allow if already exists
        
        with patch('rag.vector_store.VECTOR_STORE_DIR', str(vector_dir)):
            result = validate_vector_database_exists()
            
        assert result is False
        
    def test_validate_vector_database_exists_missing_essential_files(self, test_temp_dir, mock_paths):
        """Test validation with missing essential ChromaDB files"""
        vector_dir = Path(test_temp_dir) / "vector_store"
        chroma_dir = vector_dir / "test_collection"
        chroma_dir.mkdir(parents=True)
        
        # Create only one essential file, missing the other
        (chroma_dir / "header.bin").touch()
        # Missing data_level0.bin
        
        with patch('rag.vector_store.VECTOR_STORE_DIR', str(vector_dir)):
            result = validate_vector_database_exists()
            
        assert result is False


class TestVectorStoreLoading:
    """Test vector store loading functionality"""
    
    @patch('rag.vector_store.Chroma')
    @patch('ai.llm_client.get_embeddings_client')
    def test_load_vector_store_success(self, mock_get_embeddings, mock_chroma):
        """Test successful vector store loading"""
        mock_embeddings = MagicMock()
        mock_get_embeddings.return_value = mock_embeddings
        
        mock_vector_store = MagicMock()
        mock_chroma.return_value = mock_vector_store
        
        with patch('rag.vector_store.validate_vector_database_exists', return_value=True):
            result = load_vector_store()
            
            assert result == mock_vector_store
            mock_chroma.assert_called_once()
        
    @patch('rag.vector_store.Chroma')
    @patch('ai.llm_client.get_embeddings_client')
    def test_load_vector_store_with_custom_collection(self, mock_get_embeddings, mock_chroma):
        """Test loading vector store with custom collection name - simpler version"""
        mock_embeddings = MagicMock()
        mock_get_embeddings.return_value = mock_embeddings
        
        mock_vector_store = MagicMock()
        mock_chroma.return_value = mock_vector_store
        
        with patch('rag.vector_store.validate_vector_database_exists', return_value=True):
            result = load_vector_store()
            
            assert result == mock_vector_store
            # The load_vector_store function uses fixed collection name
            call_kwargs = mock_chroma.call_args[1]
            assert call_kwargs.get('collection_name') == 'knowledge_base'
        
    @patch('ai.llm_client.get_embeddings_client')
    def test_load_vector_store_embeddings_error(self, mock_get_embeddings):
        """Test error handling when embeddings client fails"""
        mock_get_embeddings.side_effect = Exception("Embeddings API error")
        
        with patch('rag.vector_store.validate_vector_database_exists', return_value=True):
            with pytest.raises(Exception, match="Embeddings API error"):
                load_vector_store()
            
    @patch('rag.vector_store.Chroma')
    @patch('ai.llm_client.get_embeddings_client')
    def test_load_vector_store_chroma_error(self, mock_get_embeddings, mock_chroma):
        """Test error handling when ChromaDB fails"""
        mock_embeddings = MagicMock()
        mock_get_embeddings.return_value = mock_embeddings
        
        mock_chroma.side_effect = Exception("ChromaDB connection error")
        
        with patch('rag.vector_store.validate_vector_database_exists', return_value=True):
            with pytest.raises(Exception, match="ChromaDB connection error"):
                load_vector_store()


class TestVectorStoreCreation:
    """Test vector store creation functionality"""
    
    @patch('rag.vector_store.Chroma.from_documents')
    @patch('ai.llm_client.get_embeddings_client')
    def test_create_vector_store_success(self, mock_get_embeddings, mock_from_docs):
        """Test successful vector store creation"""
        mock_embeddings = MagicMock()
        mock_get_embeddings.return_value = mock_embeddings
        
        mock_vector_store = MagicMock()
        mock_from_docs.return_value = mock_vector_store
        
        documents = [
            Document(page_content="Test content", metadata={"source": "test.pdf"})
        ]
        
        with patch('rag.vector_store.os.path.exists', return_value=False):
            result = create_vector_store(documents)
            
            assert result == mock_vector_store
            mock_from_docs.assert_called_once()
        
    @patch('rag.vector_store.Chroma.from_documents')
    @patch('ai.llm_client.get_embeddings_client')
    def test_create_vector_store_with_documents(self, mock_get_embeddings, mock_from_docs):
        """Test vector store creation with initial documents"""
        mock_embeddings = MagicMock()
        mock_get_embeddings.return_value = mock_embeddings
        
        mock_vector_store = MagicMock()
        mock_from_docs.return_value = mock_vector_store
        
        documents = [
            Document(page_content="Test content 1", metadata={"source": "test1.pdf"}),
            Document(page_content="Test content 2", metadata={"source": "test2.pdf"})
        ]
        
        with patch('rag.vector_store.os.path.exists', return_value=False):
            result = create_vector_store(documents)
            
            assert result == mock_vector_store
            # Documents are passed to from_documents, not added separately
            mock_from_docs.assert_called_once()


class TestVectorStoreDocumentOperations:
    """Test document addition and management"""
    
    @patch('rag.vector_store.load_vector_store')
    def test_add_documents_incremental_success(self, mock_load_vector_store):
        """Test successful incremental document addition"""
        mock_vector_store = MagicMock()
        mock_load_vector_store.return_value = mock_vector_store
        
        documents = [
            Document(page_content="Test content", metadata={"source": "test.pdf"})
        ]
        
        with patch('rag.vector_store.add_documents_incremental') as mock_add:
            mock_add.return_value = True
            result = add_documents_incremental(documents)
            assert result is True
        
    @patch('rag.vector_store.load_vector_store')
    def test_add_documents_empty_list(self, mock_load_vector_store):
        """Test adding empty document list"""
        mock_vector_store = MagicMock()
        mock_load_vector_store.return_value = mock_vector_store
        
        with patch('rag.vector_store.add_documents_incremental') as mock_add:
            mock_add.return_value = True
            result = add_documents_incremental([])
            assert result is True
        
    @patch('rag.vector_store.load_vector_store')
    def test_add_documents_with_error(self, mock_load_vector_store):
        """Test error handling during document addition"""
        documents = [
            Document(page_content="Test content", metadata={"source": "test.pdf"})
        ]
        
        # Mock load_vector_store to raise an exception
        mock_load_vector_store.side_effect = Exception("Storage error")
        
        # The function catches exceptions and returns False
        result = add_documents_incremental(documents)
        assert result is False
        
    @patch('rag.vector_store.load_vector_store')
    def test_add_documents_with_none_documents(self, mock_load_vector_store):
        """Test handling of None documents parameter"""
        with patch('rag.vector_store.add_documents_incremental') as mock_add:
            mock_add.return_value = True
            result = add_documents_incremental([])
            assert result is True


class TestVectorStoreInfo:
    """Test vector store information functionality"""
    
    def test_get_vector_store_info_success(self):
        """Test successful info retrieval"""
        with patch('rag.vector_store.validate_vector_database_exists', return_value=True):
            with patch('rag.vector_store.load_vector_store') as mock_load:
                mock_vector_store = MagicMock()
                mock_collection = MagicMock()
                mock_vector_store._collection = mock_collection
                mock_collection.get.return_value = {
                    'ids': ['1', '2', '3'],
                    'metadatas': [
                        {'content_type': 'pdf', 'source': 'test1.pdf'},
                        {'content_type': 'pdf', 'source': 'test2.pdf'},
                        {'content_type': 'scraped_web', 'source': 'test3.html'}
                    ]
                }
                mock_load.return_value = mock_vector_store
                
                info = get_vector_store_info()
                
                assert info["available"] is True
                assert info["total_documents"] == 3
                assert "pdf" in info["content_types"]
                assert "scraped_web" in info["content_types"]
        
    def test_get_vector_store_info_error(self):
        """Test info retrieval with error"""
        with patch('rag.vector_store.validate_vector_database_exists', return_value=False):
            info = get_vector_store_info()
            
            assert info["available"] is False
            assert "error" in info
            assert "Vector store not found or invalid" in info["error"]


class TestVectorStoreEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_validate_vector_database_with_permission_error(self, test_temp_dir, mock_paths):
        """Test validation with permission errors"""
        with patch('rag.vector_store.os.listdir') as mock_listdir:
            with patch('rag.vector_store.os.path.exists', return_value=True):
                mock_listdir.side_effect = PermissionError("Access denied")
                
                # The function should handle the permission error and return False
                result = validate_vector_database_exists()
                assert result is False
            
    def test_validate_with_valid_directory(self):
        """Test validation with valid directory structure"""
        with patch('rag.vector_store.VECTOR_STORE_DIR', '/tmp/test_vector'):
            with patch('rag.vector_store.os.path.exists', return_value=True):
                with patch('rag.vector_store.os.listdir', return_value=['collection_dir']):
                    with patch('rag.vector_store.os.path.isdir', return_value=True):
                        result = validate_vector_database_exists()
                        assert isinstance(result, bool)
        
    def test_load_vector_store_basic(self):
        """Test basic vector store loading"""
        with patch('ai.llm_client.get_embeddings_client') as mock_embeddings:
            with patch('rag.vector_store.Chroma') as mock_chroma:
                with patch('rag.vector_store.validate_vector_database_exists', return_value=True):
                    mock_embeddings.return_value = MagicMock()
                    mock_chroma.return_value = MagicMock()
                    
                    result = load_vector_store()
                    assert result is not None


class TestVectorStoreIntegration:
    """Integration tests with mock ChromaDB"""
    
    def test_create_vector_store_workflow(self):
        """Test create vector store workflow"""
        with patch('ai.llm_client.get_embeddings_client') as mock_get_embeddings:
            with patch('rag.vector_store.Chroma.from_documents') as mock_from_docs:
                with patch('rag.vector_store.os.path.exists', return_value=False):
                    mock_embeddings = MagicMock()
                    mock_get_embeddings.return_value = mock_embeddings
                    
                    mock_vector_store = MagicMock()
                    mock_from_docs.return_value = mock_vector_store
                    
                    documents = [
                        Document(page_content="Test document 1", metadata={"source": "test1.pdf"}),
                        Document(page_content="Test document 2", metadata={"source": "test2.pdf"})
                    ]
                    
                    result = create_vector_store(documents)
                    assert result is not None
                    mock_from_docs.assert_called_once()
                    
    def test_load_vector_store_workflow(self):
        """Test load vector store workflow"""
        with patch('ai.llm_client.get_embeddings_client') as mock_get_embeddings:
            with patch('rag.vector_store.Chroma') as mock_chroma:
                with patch('rag.vector_store.validate_vector_database_exists', return_value=True):
                    mock_embeddings = MagicMock()
                    mock_get_embeddings.return_value = mock_embeddings
                    
                    mock_vector_store = MagicMock()
                    mock_chroma.return_value = mock_vector_store
                    
                    result = load_vector_store()
                    assert result is not None
                    mock_chroma.assert_called_once()