"""
Pytest configuration and fixtures for UNSW CSE Chatbot Backend Tests
"""

import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import MagicMock, patch, Mock
from pathlib import Path
from datetime import datetime, timezone
import json

# Add backend to path for imports
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

# Flask and testing imports
from flask import Flask
import jwt

# Import application components
from app import app as flask_app
from config.paths import PathConfig

@pytest.fixture(scope="session")
def app():
    """Create Flask application for testing"""
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-key'
    flask_app.config['WTF_CSRF_ENABLED'] = False
    return flask_app

@pytest.fixture(scope="session")
def client(app):
    """Create Flask test client"""
    return app.test_client()

@pytest.fixture
def test_temp_dir():
    """Create temporary directory for test files"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables for testing"""
    with patch.dict(os.environ, {
        'GOOGLE_API_KEY': 'test-google-api-key',
        'GOOGLE_APPLICATION_CREDENTIALS': '/tmp/test-credentials.json',
        'SECRET_KEY': 'test-secret-key',
        'ADMIN_EMAIL': 'test@unsw.edu.au',
        'ADMIN_PASSWORD': 'test-password',
        'FLASK_ENV': 'testing'
    }):
        yield

@pytest.fixture
def mock_paths(test_temp_dir):
    """Mock PathConfig with temporary paths"""
    temp_path = Path(test_temp_dir)
    
    # Create test directory structure
    (temp_path / "documents").mkdir(exist_ok=True)
    (temp_path / "scraped_content" / "content").mkdir(parents=True, exist_ok=True)
    (temp_path / "vector_store").mkdir(exist_ok=True)
    (temp_path / "logs").mkdir(exist_ok=True)
    
    with patch.object(PathConfig, 'DATA_ROOT', temp_path):
        with patch.object(PathConfig, 'DOCUMENTS_DIR', temp_path / "documents"):
            with patch.object(PathConfig, 'SCRAPED_CONTENT_DIR', temp_path / "scraped_content"):
                with patch.object(PathConfig, 'VECTOR_STORE_DIR', temp_path / "vector_store"):
                    with patch.object(PathConfig, 'LOGS_DIR', temp_path / "logs"):
                        with patch.object(PathConfig, 'SCRAPED_CONTENT_FILES_DIR', temp_path / "scraped_content" / "content"):
                            yield temp_path

@pytest.fixture
def mock_google_api():
    """Mock Google Generative AI API"""
    with patch('google.generativeai.configure'):
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_instance = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Test response from Gemini"
            mock_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_instance
            yield mock_instance

@pytest.fixture
def mock_google_embeddings():
    """Mock Google Generative AI Embeddings"""
    with patch('langchain_google_genai.GoogleGenerativeAIEmbeddings') as mock_embeddings:
        mock_instance = MagicMock()
        mock_instance.embed_query.return_value = [0.1] * 768  # Mock embedding vector
        mock_instance.embed_documents.return_value = [[0.1] * 768, [0.2] * 768]
        mock_embeddings.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_chat_llm():
    """Mock ChatGoogleGenerativeAI"""
    with patch('langchain_google_genai.ChatGoogleGenerativeAI') as mock_chat:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value.content = "Test chat response"
        mock_chat.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_vector_store():
    """Mock ChromaDB vector store"""
    with patch('chromadb.Client') as mock_client:
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["Test document content"]],
            "metadatas": [[{"source": "test.pdf", "page": 1}]],
            "distances": [[0.5]],
            "ids": [["test_id_1"]]
        }
        mock_collection.count.return_value = 10
        mock_client.return_value.get_collection.return_value = mock_collection
        mock_client.return_value.list_collections.return_value = [
            MagicMock(name="test_collection")
        ]
        yield mock_collection

@pytest.fixture
def mock_bm25_search():
    """Mock BM25 search functionality"""
    with patch('rank_bm25.BM25Okapi') as mock_bm25:
        mock_instance = MagicMock()
        mock_instance.get_scores.return_value = [0.8, 0.6, 0.3]
        mock_bm25.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def sample_documents():
    """Sample documents for testing"""
    return [
        {
            "page_content": "COMP9900 is a capstone project course in computer science.",
            "metadata": {
                "source": "handbook.pdf",
                "page": 1,
                "course_code": "COMP9900",
                "content_type": "course_description"
            }
        },
        {
            "page_content": "The Computer Science building is located at J17.",
            "metadata": {
                "source": "campus_guide.pdf",
                "page": 5,
                "building": "J17",
                "content_type": "location_info"
            }
        }
    ]

@pytest.fixture
def sample_queries():
    """Sample queries for testing"""
    return {
        "course_info": "What is COMP9900?",
        "location": "Where is J17?",
        "greeting": "Hello",
        "comparison": "Compare COMP9900 and COMP9901",
        "non_unsw": "Tell me about University of Sydney courses",
        "navigation": "How do I get to the library?"
    }

@pytest.fixture
def sample_chat_logs():
    """Sample chat logs for testing"""
    return [
        {
            "timestamp": "2025-01-01T10:00:00+11:00",
            "session_id": "test_session_1",
            "question": "What is COMP9900?",
            "answer": "COMP9900 is a capstone project course.",
            "answered": True,
            "query_type": "rag_answered",
            "matched_files": ["handbook.pdf"],
            "response_time_ms": 500,
            "tokens_used": 100,
            "message_id": "test_msg_1"
        },
        {
            "timestamp": "2025-01-01T10:05:00+11:00", 
            "session_id": "test_session_1",
            "question": "Where is J17?",
            "answer": "J17 is the Computer Science building.",
            "answered": True,
            "query_type": "ai_answered",
            "matched_files": [],
            "response_time_ms": 300,
            "tokens_used": 50,
            "message_id": "test_msg_2"
        }
    ]

@pytest.fixture
def sample_cache_entries():
    """Sample cache entries for testing"""
    return [
        {
            "question_hash": "abc123def456",
            "question": "what is comp9900?",
            "answer": "COMP9900 is a capstone project course.",
            "answer_quality": "rag_answered",
            "matched_files": ["handbook.pdf"],
            "created_at": "2025-01-01T10:00:00+11:00",
            "cache_id": "cache_1"
        }
    ]

@pytest.fixture
def mock_jwt_token():
    """Mock JWT token for admin authentication"""
    def create_token(role="admin", expired=False):
        payload = {
            "role": role,
            "exp": datetime.now(timezone.utc).timestamp() + (3600 if not expired else -3600)
        }
        return jwt.encode(payload, "test-secret-key", algorithm="HS256")
    return create_token

@pytest.fixture
def mock_file_system(test_temp_dir):
    """Mock file system operations"""
    class MockFileSystem:
        def __init__(self, base_dir):
            self.base_dir = Path(base_dir)
            
        def create_file(self, path, content=""):
            """Create a test file with content"""
            file_path = self.base_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            return file_path
            
        def create_json_file(self, path, data):
            """Create a JSON file with data"""
            file_path = self.base_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(json.dumps(data, ensure_ascii=False))
            return file_path
            
    return MockFileSystem(test_temp_dir)

# Test utilities
def assert_valid_response(response_data):
    """Assert that a response has valid structure"""
    assert "answer" in response_data
    assert "answered" in response_data
    assert isinstance(response_data["answered"], bool)

def assert_valid_cache_entry(cache_entry):
    """Assert that a cache entry has valid structure"""
    required_fields = ["question_hash", "question", "answer", "created_at"]
    for field in required_fields:
        assert field in cache_entry

def assert_valid_chat_log(chat_log):
    """Assert that a chat log entry has valid structure"""
    required_fields = ["timestamp", "session_id", "question", "answer", "answered"]
    for field in required_fields:
        assert field in chat_log