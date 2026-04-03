"""
Unit tests for AI LLM Client module
Tests the management of Google Generative AI connections and configurations
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the module under test
from ai.llm_client import (
    get_chat_llm, 
    get_embeddings_client, 
    get_genai_model,
    reset_clients
)

from test.mocks.mock_llm import MockGenerativeModel, MockChatGoogleGenerativeAI, MockGoogleGenerativeAIEmbeddings


class TestLLMClient:
    """Test LLM client management and configuration"""
    
    def setup_method(self):
        """Reset clients before each test"""
        reset_clients()
        
    def teardown_method(self):
        """Clean up after each test"""
        reset_clients()

    @patch('ai.llm_client.ChatGoogleGenerativeAI')
    def test_get_chat_llm_singleton_creation(self, mock_chat_class):
        """Test that chat LLM client is created as singleton"""
        mock_instance = MagicMock()
        mock_chat_class.return_value = mock_instance
        
        # First call should create instance
        client1 = get_chat_llm()
        assert client1 == mock_instance
        mock_chat_class.assert_called_once_with(model="gemini-2.5-flash")
        
        # Second call should return same instance
        client2 = get_chat_llm()
        assert client2 == client1
        # Should not create new instance
        mock_chat_class.assert_called_once()
        
    @patch('ai.llm_client.ChatGoogleGenerativeAI')
    def test_get_chat_llm_custom_model(self, mock_chat_class):
        """Test chat LLM with custom model"""
        mock_instance = MagicMock()
        mock_chat_class.return_value = mock_instance
        
        client = get_chat_llm("gemini-pro")
        mock_chat_class.assert_called_once_with(model="gemini-pro")
        
    @patch('ai.llm_client.HuggingFaceEmbeddings')
    def test_get_embeddings_client_singleton_creation(self, mock_embeddings_class):
        """Test that embeddings client is created as singleton"""
        mock_instance = MagicMock()
        mock_embeddings_class.return_value = mock_instance

        # First call should create instance
        client1 = get_embeddings_client()
        assert client1 == mock_instance
        mock_embeddings_class.assert_called_once_with(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )

        # Second call should return same instance
        client2 = get_embeddings_client()
        assert client2 == client1
        mock_embeddings_class.assert_called_once()

    @patch('ai.llm_client.HuggingFaceEmbeddings')
    def test_get_embeddings_client_custom_model(self, mock_embeddings_class):
        """Test embeddings client with custom model"""
        mock_instance = MagicMock()
        mock_embeddings_class.return_value = mock_instance

        client = get_embeddings_client("custom-model")
        mock_embeddings_class.assert_called_once_with(
            model_name="custom-model",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        
    @patch('ai.llm_client.genai.GenerativeModel')
    def test_get_genai_model_singleton_creation(self, mock_genai_class):
        """Test that native GenerativeAI model is created as singleton"""
        mock_instance = MagicMock()
        mock_genai_class.return_value = mock_instance
        
        # First call should create instance
        model1 = get_genai_model()
        assert model1 == mock_instance
        mock_genai_class.assert_called_once_with("gemini-2.5-flash")
        
        # Second call should return same instance
        model2 = get_genai_model()
        assert model2 == model1
        mock_genai_class.assert_called_once()
        
    @patch('ai.llm_client.genai.GenerativeModel')
    def test_get_genai_model_custom_model(self, mock_genai_class):
        """Test native GenerativeAI model with custom model"""
        mock_instance = MagicMock()
        mock_genai_class.return_value = mock_instance
        
        model = get_genai_model("gemini-pro")
        mock_genai_class.assert_called_once_with("gemini-pro")
        
    @patch('ai.llm_client.ChatGoogleGenerativeAI')
    @patch('ai.llm_client.HuggingFaceEmbeddings')
    @patch('ai.llm_client.genai.GenerativeModel')
    def test_reset_clients(self, mock_genai, mock_embeddings, mock_chat):
        """Test that reset_clients clears all singletons"""
        # Create instances
        get_chat_llm()
        get_embeddings_client()
        get_genai_model()
        
        # Verify instances were created
        mock_chat.assert_called_once()
        mock_embeddings.assert_called_once()
        mock_genai.assert_called_once()
        
        # Reset clients
        reset_clients()
        
        # Create new instances - should call constructors again
        get_chat_llm()
        get_embeddings_client()
        get_genai_model()
        
        # Should have been called twice now
        assert mock_chat.call_count == 2
        assert mock_embeddings.call_count == 2
        assert mock_genai.call_count == 2
        
    @patch('ai.llm_client.genai.configure')
    def test_genai_configuration(self, mock_configure):
        """Test that Google Generative AI is configured with API key"""
        # Force module reload to trigger configuration
        import importlib
        import ai.llm_client
        importlib.reload(ai.llm_client)
        mock_configure.assert_called()
        
    def test_google_credentials_env_var(self):
        """Test that Google application credentials environment variable is set"""
        # Check that the environment variable is set (from conftest.py mock)
        assert 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ
        
    @patch.dict(os.environ, {}, clear=True)
    @patch('ai.llm_client.genai.configure')
    def test_missing_api_key_environment(self, mock_configure):
        """Test behavior when GOOGLE_API_KEY is missing"""
        # Force module reload to trigger configuration with empty env
        import importlib
        import ai.llm_client
        importlib.reload(ai.llm_client)
        mock_configure.assert_called_with(api_key=None)


class TestLLMClientIntegration:
    """Integration tests for LLM client with mocked external dependencies"""
    
    def setup_method(self):
        """Reset clients before each test"""
        reset_clients()
        
    @patch('ai.llm_client.ChatGoogleGenerativeAI')
    def test_chat_llm_error_handling(self, mock_chat_class):
        """Test error handling in chat LLM creation"""
        mock_chat_class.side_effect = Exception("API connection failed")
        
        with pytest.raises(Exception, match="API connection failed"):
            get_chat_llm()
            
    @patch('ai.llm_client.HuggingFaceEmbeddings')
    def test_embeddings_client_error_handling(self, mock_embeddings_class):
        """Test error handling in embeddings client creation"""
        mock_embeddings_class.side_effect = Exception("Embeddings model load failed")

        with pytest.raises(Exception, match="Embeddings model load failed"):
            get_embeddings_client()
            
    @patch('ai.llm_client.genai.GenerativeModel')
    def test_genai_model_error_handling(self, mock_genai_class):
        """Test error handling in native GenAI model creation"""
        mock_genai_class.side_effect = Exception("Model not found")
        
        with pytest.raises(Exception, match="Model not found"):
            get_genai_model()


class TestLLMClientConfiguration:
    """Test configuration and credential handling"""
    
    @patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': '/test/path/key.json'})
    def test_custom_credentials_path(self):
        """Test that custom credentials path is respected"""
        assert os.environ['GOOGLE_APPLICATION_CREDENTIALS'] == '/test/path/key.json'
        
    @patch.dict(os.environ, {}, clear=True)
    def test_default_credentials_path(self):
        """Test that default credentials path is set when not provided"""
        # Re-import to trigger path setting
        import importlib
        import ai.llm_client
        importlib.reload(ai.llm_client)
        
        # Should have set default path
        assert 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ
        credentials_path = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
        assert credentials_path.endswith('config/key.json')


class TestLLMClientEdgeCases:
    """Test edge cases and error scenarios"""
    
    def setup_method(self):
        """Reset clients before each test"""
        reset_clients()
        
    def test_empty_model_name(self):
        """Test behavior with empty model name"""
        with patch('ai.llm_client.ChatGoogleGenerativeAI') as mock_chat:
            mock_instance = MagicMock()
            mock_chat.return_value = mock_instance
            
            client = get_chat_llm("")
            mock_chat.assert_called_once_with(model="")
            
    def test_none_model_name(self):
        """Test behavior with None model name"""
        with patch('ai.llm_client.ChatGoogleGenerativeAI') as mock_chat:
            mock_instance = MagicMock()
            mock_chat.return_value = mock_instance
            
            client = get_chat_llm(None)
            mock_chat.assert_called_once_with(model=None)
            
    @patch('ai.llm_client.Path')
    def test_invalid_credentials_path(self, mock_path):
        """Test handling of invalid credentials path"""
        mock_path.side_effect = Exception("Invalid path")
        
        # Should not raise exception during import
        try:
            import importlib
            import ai.llm_client
            importlib.reload(ai.llm_client)
        except Exception as e:
            pytest.fail(f"Should handle invalid path gracefully: {e}")


# Performance and stress tests
class TestLLMClientPerformance:
    """Test performance characteristics of LLM client"""
    
    def setup_method(self):
        """Reset clients before each test"""
        reset_clients()
        
    @patch('ai.llm_client.ChatGoogleGenerativeAI')
    def test_concurrent_singleton_access(self, mock_chat_class):
        """Test that concurrent access to singleton is thread-safe"""
        import threading
        import time
        
        mock_instance = MagicMock()
        mock_chat_class.return_value = mock_instance
        
        results = []
        
        def get_client():
            time.sleep(0.001)  # Small delay to increase chance of race condition
            client = get_chat_llm()
            results.append(client)
            
        # Create multiple threads
        threads = [threading.Thread(target=get_client) for _ in range(10)]
        
        # Start all threads
        for thread in threads:
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # All results should be the same instance
        assert len(results) == 10
        assert all(client == results[0] for client in results)
        
        # Constructor should only be called once
        mock_chat_class.assert_called_once()