"""
Mock implementations for Google Generative AI LLM services
"""

from unittest.mock import MagicMock
from typing import Dict, List, Any, Optional


class MockGenerativeModel:
    """Mock Google Generative AI Model"""
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self._responses = {}
        self._default_response = "This is a test response from mock Gemini."
        self.call_count = 0
        
    def set_response(self, prompt_key: str, response: str):
        """Set a specific response for a prompt pattern"""
        self._responses[prompt_key] = response
        
    def set_default_response(self, response: str):
        """Set default response for unmatched prompts"""
        self._default_response = response
        
    def generate_content(self, prompt: str, **kwargs) -> MagicMock:
        """Mock content generation"""
        self.call_count += 1
        
        # Find matching response based on prompt content
        response_text = self._default_response
        for key, value in self._responses.items():
            if key.lower() in prompt.lower():
                response_text = value
                break
                
        # Create mock response object
        mock_response = MagicMock()
        mock_response.text = response_text
        mock_response.parts = [MagicMock(text=response_text)]
        
        return mock_response


class MockChatGoogleGenerativeAI:
    """Mock LangChain ChatGoogleGenerativeAI"""
    
    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model = model
        self._responses = {}
        self._default_response = "Test chat response"
        self.call_count = 0
        
    def set_response(self, prompt_key: str, response: str):
        """Set a specific response for a prompt pattern"""
        self._responses[prompt_key] = response
        
    def invoke(self, messages, **kwargs) -> MagicMock:
        """Mock message invocation"""
        self.call_count += 1
        
        # Extract prompt content from messages
        prompt_content = ""
        if isinstance(messages, list):
            prompt_content = " ".join([msg.content for msg in messages if hasattr(msg, 'content')])
        elif hasattr(messages, 'content'):
            prompt_content = messages.content
        else:
            prompt_content = str(messages)
            
        # Find matching response
        response_text = self._default_response
        for key, value in self._responses.items():
            if key.lower() in prompt_content.lower():
                response_text = value
                break
                
        # Create mock response
        mock_response = MagicMock()
        mock_response.content = response_text
        return mock_response


class MockGoogleGenerativeAIEmbeddings:
    """Mock Google Generative AI Embeddings"""
    
    def __init__(self, model: str = "models/embedding-001"):
        self.model = model
        self.embedding_dim = 768
        self.call_count = 0
        
    def embed_query(self, text: str) -> List[float]:
        """Mock query embedding"""
        self.call_count += 1
        # Generate deterministic embedding based on text hash
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        return [(hash_val % 1000) / 1000.0] * self.embedding_dim
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Mock document embeddings"""
        self.call_count += len(texts)
        return [self.embed_query(text) for text in texts]


# Response templates for different types of queries
MOCK_RESPONSES = {
    "course_info": {
        "comp9900": "COMP9900 is a capstone project course where students work in teams to develop a significant software project. It runs over two terms and is the culminating experience for computer science students.",
        "comp9021": "COMP9021 Principles of Programming teaches fundamental programming concepts using Python. It covers data structures, algorithms, and object-oriented programming principles.",
        "prerequisites": "The prerequisites for this course include completion of fundamental programming courses and data structures."
    },
    
    "location": {
        "j17": "J17 is the Computer Science and Engineering building located in the heart of UNSW campus. You can find it using the campus map.",
        "library": "The UNSW Library is located in the central part of campus and offers study spaces, resources, and research assistance.",
        "navigation": "NAVIGATION_QUERY"
    },
    
    "safety": {
        "non_unsw": "REDIRECT: I can only help with UNSW-related questions. Please ask about UNSW programs and courses.",
        "inappropriate": "I can only help with UNSW-related academic questions."
    },
    
    "greeting": {
        "hello": "Hello! Welcome to UNSW CSE Open Day! I'm here to help answer your questions about Computer Science and Engineering at UNSW.",
        "thanks": "You're welcome! Is there anything else you'd like to know about UNSW CSE?"
    },
    
    "query_enhancement": {
        "what is comp9900": "COMP9900 overview description prerequisites",
        "where is j17": "NAVIGATION_QUERY",
        "tell me about sydney uni": "REDIRECT: I can only help with UNSW-related questions.",
        "prerequisites for it": "COMP9900 prerequisites requirements"  # With context
    }
}


def create_mock_llm_with_responses(response_type: str = "course_info") -> MockGenerativeModel:
    """Create a mock LLM with predefined responses"""
    mock_llm = MockGenerativeModel()
    
    if response_type in MOCK_RESPONSES:
        for key, value in MOCK_RESPONSES[response_type].items():
            mock_llm.set_response(key, value)
            
    return mock_llm


def create_mock_chat_llm_with_responses(response_type: str = "course_info") -> MockChatGoogleGenerativeAI:
    """Create a mock Chat LLM with predefined responses"""
    mock_chat = MockChatGoogleGenerativeAI()
    
    if response_type in MOCK_RESPONSES:
        for key, value in MOCK_RESPONSES[response_type].items():
            mock_chat.set_response(key, value)
            
    return mock_chat