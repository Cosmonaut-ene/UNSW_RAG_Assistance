# RAG (Retrieval-Augmented Generation) Module

## Overview

The RAG module is the core component of the UNSW Open Day chatbot system, providing intelligent question answering through a combination of document retrieval, semantic search, and large language model generation. It integrates Google's Gemini AI with ChromaDB vector storage and hybrid search capabilities.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PDF Docs      │    │  Scraped Web     │    │  User Query     │
│   (Knowledge)   │    │  Content (JSON)  │    │                 │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                      │                       │
          │                      │                       │
          ▼                      ▼                       ▼
    ┌─────────────────────────────────────────┐    ┌──────────────┐
    │           Document Loading              │    │   Safety     │
    │     • PDF Processing (PyMuPDF)         │    │   Check      │
    │     • JSON Content Loading             │    │  (Gemini)    │
    │     • Metadata Extraction              │    │              │
    └─────────────────┬───────────────────────┘    └──────┬───────┘
                      │                                   │
                      ▼                                   ▼
    ┌─────────────────────────────────────────┐    ┌──────────────┐
    │           Document Chunking             │    │   Query      │
    │     • spaCy Sentence Splitting         │    │  Rewriting   │
    │     • Markdown Header Preservation     │    │  (Gemini)    │
    │     • Context-Aware Segmentation       │    │              │
    └─────────────────┬───────────────────────┘    └──────┬───────┘
                      │                                   │
                      ▼                                   ▼
    ┌─────────────────────────────────────────┐    ┌──────────────┐
    │         Vector Store Creation           │    │   Hybrid     │
    │     • Google Embeddings (embedding-001)│    │   Search     │
    │     • ChromaDB Storage                  │    │   Pipeline   │
    │     • Automatic Index Updates          │    │              │
    └─────────────────┬───────────────────────┘    └──────┬───────┘
                      │                                   │
                      │            ┌─────────────────────┐│
                      │            │                     ││
                      ▼            ▼                     ▼▼
    ┌─────────────────────────────────────────────────────────────┐
    │                    Answer Generation                        │
    │     • Context Assembly                                      │
    │     • Conversation History Integration                      │
    │     • Gemini-2.5-Flash Response Generation                  │
    │     • Source Attribution & Link Extraction                  │
    └─────────────────────────────────────────────────────────────┘
```

## Core Features

### 🔍 Multi-Modal Search
- **Semantic Search**: Vector similarity using Google embeddings
- **Keyword Search**: Pattern-based text matching with course code intelligence
- **Hybrid Search**: Combines both methods with intelligent scoring

### 📚 Document Processing
- **PDF Support**: Academic documents and handbooks
- **Web Content**: Scraped JSON from UNSW handbook
- **Smart Chunking**: Context-preserving document segmentation
- **Metadata Preservation**: Source attribution and document structure

### 🧠 AI Integration
- **Google Gemini**: Primary LLM for generation and safety
- **Query Enhancement**: Automatic query rewriting for better retrieval
- **Safety Filtering**: Built-in content moderation
- **Conversation Memory**: Context-aware multi-turn conversations

### ⚡ Performance Optimization
- **Incremental Updates**: Only rebuilds when content changes
- **Lazy Loading**: Components initialized on demand
- **Vector Caching**: Persistent ChromaDB storage
- **Threshold Filtering**: Quality-based result filtering

## Key Components

### 1. Document Loading (`load_documents_*`)
- **`load_documents_from_folder()`**: PDF processing with PyMuPDF
- **`load_scraped_documents()`**: JSON content from web scrapers
- **Metadata enrichment**: Content type tagging and source tracking

### 2. Document Chunking
- **`split_documents_spacy()`**: Sentence-based chunking for PDFs
- **`split_documents_markdown()`**: Structure-preserving for web content
- **`split_documents()`**: Traditional character-based chunking

### 3. Vector Store Management
- **`create_vector_store()`**: ChromaDB index creation
- **`update_vector_store()`**: Intelligent rebuilding
- **`_validate_vector_database_exists()`**: Health checking

### 4. Query Processing Pipeline
- **`ask_with_hybrid_search()`**: Main query processing function
- **`ask_with_rag_and_fallback()`**: Traditional RAG with fallback
- **`rewrite_query_gemini()`**: Query enhancement
- **`is_query_safe_by_gemini()`**: Safety validation

## Configuration

### Environment Variables
```bash
# Required API Keys
GOOGLE_API_KEY=your_gemini_api_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/service_account.json

# Optional Paths
RAG_KNOWLEDGE_BASE_DIR=/custom/docs/path
RAG_VECTOR_STORE_DIR=/custom/vector/path
```

### Directory Structure
```
rag/
├── docs/                    # PDF knowledge base
├── scraped_content/         
│   └── content/            # JSON scraped content
├── vector_store/           # ChromaDB persistence
│   └── source_files.txt    # Change tracking
└── *.py                    # Module files
```

## Usage Examples

### Basic Setup
```python
from rag.gemini3 import build_rag_qa_chain, ask_with_hybrid_search

# Initialize the system
qa_chain = build_rag_qa_chain()

# Process a query
result = ask_with_hybrid_search(
    question="Tell me about COMP9020",
    qa_chain=qa_chain,
    conversation_history=[]
)

print(result['answer'])
print(f"Sources: {result['matched_files']}")
```

### Advanced Configuration
```python
from rag.hybrid_search import HybridSearchEngine

# Custom threshold configuration
engine = HybridSearchEngine(
    content_dir="scraped_content/content",
    min_hybrid_score=60.0,      # Lower threshold for more results
    min_keyword_score=15.0,     # Higher keyword requirement
    min_rag_score=40.0          # Lower semantic requirement
)
```

### Vector Store Management
```python
from rag.gemini3 import (
    force_rebuild_vector_store,
    get_content_sources_summary,
    update_vector_store_with_scraped
)

# Force rebuild
success = force_rebuild_vector_store()

# Get status information
summary = get_content_sources_summary()
print(f"Total sources: {summary['total_sources']}")

# Update with new scraped content
update_vector_store_with_scraped()
```

## API Reference

### Main Functions

#### `ask_with_hybrid_search(question, qa_chain, conversation_history=None)`
Primary query processing function using hybrid search.

**Parameters:**
- `question` (str): User query
- `qa_chain`: Initialized RAG chain
- `conversation_history` (list, optional): Previous conversation turns

**Returns:**
```python
{
    "answer": str,              # Generated response
    "sources": list,            # Source document content
    "matched_files": list,      # Source file names
    "safety_blocked": bool,     # Whether query was blocked
    "search_type": str          # Search method used
}
```

#### `build_rag_qa_chain()`
Initializes the complete RAG system.

**Returns:** LangChain RetrievalQA chain object

### Utility Functions

#### `get_content_sources_summary()`
Returns detailed information about content sources and vector store status.

#### `force_rebuild_vector_store()`
Forces complete rebuilding of the vector index regardless of change detection.

## Integration Points

### With Query Processor
The RAG module integrates with the main query processor for:
- Request routing and fallback handling
- Conversation history management
- Response formatting and logging

### With Scrapers Module
Automatically processes content from web scrapers:
- JSON file monitoring
- Incremental content updates
- Source change detection

### With Admin Interface
Provides administrative capabilities:
- Vector store status monitoring
- Manual rebuild triggers
- Content source inspection

## Performance Characteristics

### Typical Response Times
- **Vector Search**: 100-300ms
- **Hybrid Search**: 200-500ms  
- **Full Pipeline**: 1-3 seconds
- **Cold Start**: 5-10 seconds

### Memory Usage
- **Base System**: ~200MB
- **Vector Store**: ~50MB per 1000 documents
- **LLM Processing**: ~500MB peak

### Scalability Limits
- **Documents**: Up to 10,000 efficiently
- **Concurrent Users**: 5-10 (dependent on Gemini API limits)
- **Vector Dimensions**: 768 (Google embeddings)

## Error Handling

The system implements comprehensive error handling:

- **API Failures**: Graceful fallback to alternative methods
- **Content Errors**: Skip corrupted documents with logging
- **Vector Store Issues**: Automatic rebuild attempts
- **Safety Violations**: Clear user feedback without details
- **Resource Limits**: Queue management and rate limiting

## Monitoring and Debugging

### Logging Levels
```python
[Gemini3] System initialization and major operations
[HybridSearch] Search execution and filtering
[QueryProcessor] Request routing and response handling
[AdminStore] Data persistence and retrieval
```

### Debug Features
- Detailed source attribution in responses
- Score breakdown for search results
- Vector store validation and health checks
- Performance timing information

## Security Considerations

- **API Key Management**: Secure environment variable handling
- **Content Filtering**: Gemini safety checks on all inputs
- **Data Privacy**: Local vector storage, no external data sharing
- **Input Validation**: Sanitization of user queries and file content

This module serves as the intelligent core of the UNSW Open Day chatbot, providing accurate, contextual, and safe responses to user queries about academic programs and courses.