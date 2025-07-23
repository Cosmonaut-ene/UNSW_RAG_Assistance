[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=19704823&assignment_repo_type=AssignmentRepo)

# UNSW CSE Chatbot Project - Comprehensive Analysis

## Project Overview

This is an AI-powered chatbot system designed for UNSW CSE Open Day, built as a capstone project (COMP9900). The system provides intelligent question answering about UNSW Computer Science and Engineering programs using Retrieval-Augmented Generation (RAG) with Google Gemini AI.

## System Architecture

### Technology Stack

- **Backend**: Python Flask with RESTful API design
- **Frontend**: Vue.js 3 with Element Plus UI components
- **AI/ML**: Google Gemini AI (gemini-2.5-flash) with LangChain
- **Vector Database**: ChromaDB for semantic search
- **Data Storage**: JSONL files for chat logs and feedback
- **Web Scraping**: Selenium + BeautifulSoup for content collection
- **Deployment**: Docker containers with nginx

### Core Components

#### 1. Backend API (`backend/`)

**Main Application (`app.py`)**

- Flask application with CORS enabled
- Two main blueprints: user routes (`/api`) and admin routes (`/api/admin`)

**Route Structure:**

- **User Routes (`routes/user.py`)**:
  - `POST /api/query` - Main chat endpoint
  - `POST /api/feedback` - User feedback collection
- **Admin Routes (`routes/admin.py`)**:
  - Authentication: `POST /login`, `GET /verify-token`
  - File Management: `POST /upload`, `GET /files`, `DELETE /delete/<filename>`
  - Query Management: `GET /queries`, `POST /update-query`, `DELETE /delete-query/<id>`
  - Scraping Control: `POST /scrapers/discover`, `POST /scrapers/scrape`
  - Vector Store: `POST /vector-store/rebuild`

#### 2. RAG System (`backend/rag/`)

**Core RAG Engine (`gemini3.py`)**

- Document loading from PDFs and scraped JSON content
- Intelligent chunking with spaCy sentence splitting
- Google embeddings (embedding-001) with ChromaDB vector storage
- Hybrid search combining semantic and keyword matching
- Safety filtering and query rewriting with Gemini

**Hybrid Search (`hybrid_search.py`)**

- Combines vector similarity search with keyword pattern matching
- Course code recognition (COMP, INFS, ZEIT, etc.)
- Configurable scoring thresholds for quality control

#### 3. Services Layer (`backend/services/`)

- **Authentication (`auth.py`)**: JWT-based admin authentication
- **Query Processing (`query_processor.py`)**: Request routing, conversation history, response formatting
- **Log Store (`log_store.py`)**: JSONL-based chat log persistence with feedback tracking
- **Export (`export_chatlog.py`)**: Data export functionality

#### 4. Web Scraping System (`backend/scrapers/`)

- **Link Discovery (`link_discovery.py`)**: Automatic URL discovery from UNSW handbook
- **Page Scraper (`page_scraper.py`)**: Selenium-based content extraction
- **Monitor (`monitor.py`)**: Change detection and incremental updates
- **Configuration (`config.py`)**: Centralized scraping settings

#### 5. Frontend (`frontend/`)

**Vue.js Application Structure:**

- **Main App (`App.vue`)**: Simple router-view container
- **Pages**:
  - `Chatbot.vue` - Main user interface with real-time chat
  - `Admin.vue` - Administrative dashboard
  - `Login.vue` - Admin authentication
- **Components**:
  - `LoadingSpinner.vue` - Chat loading animation
  - `admin/FileManagement.vue` - PDF document management
  - `admin/QueryManagement.vue` - Chat log and feedback management

**Key Frontend Features:**

- Real-time typewriter effect for AI responses
- Session-based conversation tracking
- User feedback system (like/dislike/copy)
- Responsive design with dark mode support
- Admin authentication with JWT tokens

## Data Models & Storage

### Chat Log Schema (JSONL format in `backend/logs/chat_logs.jsonl`)

```json
{
  "message_id": "uuid",
  "timestamp": "ISO8601",
  "session_id": "string",
  "question": "string",
  "answer": "string",
  "status": "answered|unanswered|safety_blocked",
  "ai_answered": boolean,
  "matched_files": ["array"],
  "user_feedback": "positive|negative|copy",
  "feedback_time": "ISO8601",
  "admin_answered": boolean,
  "admin_response_time": "ISO8601",
  "safety_blocked": boolean
}
```

### Vector Store

- **Technology**: ChromaDB with Google embeddings
- **Location**: `backend/rag/vector_store/`
- **Content Types**: PDF documents + scraped web content
- **Metadata**: Source files, content type, update tracking

### Scraped Content Storage

- **Format**: JSON files in `backend/rag/scraped_content/content/`
- **Naming**: URL-based filenames (sanitized)
- **Metadata**: URLs, scraping timestamps in `metadata.json`

## System Workflow

### 1. User Query Processing Flow

```
User Input → Safety Check → Query Rewrite → Hybrid Search →
Context Assembly → Gemini Generation → Response + Sources →
Feedback Collection → Log Storage
```

### 2. Admin Content Management Flow

```
PDF Upload → Automatic Vector Store Update →
Content Discovery → Manual Review → Scraping Approval →
Vector Store Rebuild → System Ready
```

### 3. Knowledge Base Update Flow

```
Scheduled/Manual Discovery → Link Quality Check →
Content Scraping → JSON Storage → Vector Store Update →
Change Detection → Incremental Updates
```

## Key Features

### For End Users

- **Natural Language Chat**: Context-aware conversations about UNSW CSE
- **Real-time Responses**: Typewriter effect with source attribution
- **Feedback System**: Like/dislike/copy actions for continuous improvement
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark Mode**: User preference toggle

### For Administrators

- **Content Management**: Upload PDFs, manage knowledge base
- **Query Analytics**: View unanswered questions and negative feedback
- **Response Editing**: Update AI responses or provide manual answers
- **Scraping Control**: Discover new content, manage scraping operations
- **Export Functions**: Download chat logs and analytics
- **Vector Store Management**: Force rebuilds, monitor system health

### AI/ML Capabilities

- **Hybrid Search**: Combines semantic similarity with keyword matching
- **Safety Filtering**: Gemini-based content moderation
- **Query Enhancement**: Automatic query rewriting for better retrieval
- **Conversation Memory**: Multi-turn conversation context
- **Source Attribution**: Transparent citation of information sources

## Deployment & Infrastructure

### Docker Configuration

- **Development**: `docker-compose.dev.yml` with hot reloading
- **Production**: `docker-compose.yml` with nginx reverse proxy
- **Backend Container**: Python 3.12 with requirements.txt
- **Frontend Container**: Node.js build + nginx static serving

### Environment Configuration

- API keys via environment variables (.env file)
- Configurable admin credentials
- Flexible directory paths for knowledge base and vector storage

### Scalability Considerations

- ChromaDB can handle ~10,000 documents efficiently
- Stateless backend design for horizontal scaling
- Session-based conversation tracking
- Incremental vector store updates

## Security Features

- JWT-based admin authentication with expiration
- Input sanitization and safety filtering
- Secure file upload with type validation
- Environment variable protection for API keys
- CORS configuration for cross-origin requests

---

This system represents a sophisticated implementation of modern RAG architecture, combining traditional information retrieval with large language models to provide accurate, contextual responses about academic programs while maintaining administrative oversight and continuous improvement capabilities.
