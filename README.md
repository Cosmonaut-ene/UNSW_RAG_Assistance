# UNSW CSE Open Day Chatbot

A COMP9900 capstone project providing an AI-powered chatbot for UNSW Computer Science & Engineering Open Day visitors. The system uses an advanced Retrieval-Augmented Generation (RAG) pipeline — orchestrated by LangGraph — with Google Gemini 2.5 Flash for accurate information about UNSW CSE programs, courses, and campus facilities.

## System Overview

This chatbot combines:

- **Google Gemini 2.5 Flash** — natural language generation and chat
- **sentence-transformers/all-MiniLM-L6-v2** — local embedding model (no API quota, runs inside Docker)
- **ChromaDB** — vector database for semantic document search
- **BM25** — keyword search for improved retrieval accuracy
- **LangGraph** — graph-based RAG pipeline orchestration (safety → rewrite → HyDE → retrieve → rerank → grade → generate → hallucination check)
- **HyDE** — Hypothetical Document Embeddings, improves fuzzy query retrieval
- **CRAG** — Corrective RAG document grading, filters low-relevance chunks before generation
- **Cross-encoder reranking** — ms-marco-MiniLM-L-6-v2, re-scores retrieved chunks for precision
- **Web scraping** — Selenium + BeautifulSoup for up-to-date UNSW handbook content
- **PDF processing** — PyMuPDF with Gemini-powered contextual chunk summarisation

## Architecture

### Backend (Python Flask)

| Module | Description |
|--------|-------------|
| `ai/llm_client.py` | Google Gemini client; chat uses gemini-2.5-flash, embeddings use local sentence-transformers |
| `ai/prompt_manager.py` | Prompt templates and engineering |
| `services/query_processor.py` | Entry point: cache check → invokes LangGraph graph |
| `rag/graph_rag.py` | **LangGraph core RAG graph** — replaces manual if/elif orchestration |
| `rag/reranker.py` | **Cross-encoder reranking** (ms-marco-MiniLM-L-6-v2) |
| `rag/hyde.py` | **HyDE** hypothetical document generation, improves low-specificity queries |
| `rag/retrieval_evaluator.py` | **CRAG** document relevance grading |
| `rag/vector_store.py` | ChromaDB vector store operations |
| `rag/bm25_search.py` | BM25 keyword search |
| `rag/search_engine.py` | Hybrid search: semantic + BM25 combined scoring |
| `rag/document_loader.py` | PDF and scraped content processing |
| `rag/text_splitter.py` | Intelligent text chunking with contextual prefix |
| `rag/chain_builder.py` | RAG chain construction utilities |
| `rag/incremental_vectorstore.py` | Background vector store update queue |
| `scrapers/` | Selenium + BeautifulSoup web scraping pipeline |
| `routes/user.py` | Public chat API endpoints |
| `routes/admin.py` | Admin management API endpoints |
| `services/auth.py` | JWT-based admin authentication |
| `evaluation/` | RAGAS evaluation datasets and scripts |

### Frontend (Vue 3)

- **Vue 3** with Composition API and `<script setup>` syntax
- **Element Plus** UI component library
- **Vite** for fast development and building
- **Markdown-it** for rendering formatted bot responses
- **Vue Router** for navigation between pages

### Data Storage

- **Documents**: PDF files in `data/knowledge_base/documents/`
- **Scraped Content**: UNSW handbook data in `data/knowledge_base/scraped_content/`
- **Vector Store**: ChromaDB database in `data/knowledge_base/vector_store/`
- **Chat Logs**: Conversation logs in `data/knowledge_base/logs/chat_logs.jsonl`

## Project Structure

```
capstone-project-25t2-9900-f10a-almond/
├── backend/
│   ├── ai/                           # AI processing modules
│   │   ├── llm_client.py            # Gemini client (chat) + local embedding model
│   │   ├── prompt_manager.py        # Prompt templates
│   │   └── safety_checker.py        # Content safety validation
│   ├── rag/                         # Retrieval-Augmented Generation
│   │   ├── graph_rag.py             # LangGraph RAG pipeline (core orchestration)
│   │   ├── reranker.py              # Cross-encoder reranking (ms-marco-MiniLM-L-6-v2)
│   │   ├── hyde.py                  # HyDE hypothetical document generation
│   │   ├── retrieval_evaluator.py   # CRAG document relevance grading
│   │   ├── vector_store.py          # ChromaDB operations
│   │   ├── bm25_search.py           # BM25 keyword search
│   │   ├── search_engine.py         # Hybrid search coordinator
│   │   ├── document_loader.py       # PDF and content processing
│   │   ├── text_splitter.py         # Intelligent text chunking
│   │   ├── chain_builder.py         # RAG chain construction
│   │   └── incremental_vectorstore.py # Background vector store updates
│   ├── scrapers/                    # Web content extraction
│   │   ├── services/                # Scraping service implementations
│   │   ├── core/                    # Base scraper classes and types
│   │   └── utils/                   # Scraping utilities
│   ├── services/                    # Business logic services
│   │   ├── query_processor.py       # Main query orchestration (LangGraph entry point)
│   │   ├── async_vectorstore_updater.py # Async vector store update service
│   │   ├── auth.py                  # Admin authentication
│   │   ├── log_store.py             # Chat logging and storage
│   │   └── export_chatlog.py        # Chat log export functionality
│   ├── evaluation/                  # RAGAS evaluation
│   │   └── datasets.py              # 50+ ground truth test cases (5 categories)
│   ├── routes/                      # Flask API endpoints
│   │   ├── user.py                  # Public chat endpoints
│   │   └── admin.py                 # Admin management endpoints
│   ├── config/                      # Configuration management
│   │   └── paths.py                 # Path configuration
│   ├── scripts/                     # Utility scripts
│   │   ├── evaluation_benchmark.py  # RAGAS benchmark runner
│   │   └── run_evaluation.py        # Evaluation entry point
│   ├── test/                        # Test suite (209 tests)
│   │   ├── unit/                    # Unit tests
│   │   │   ├── test_ai/            # AI module tests
│   │   │   ├── test_rag/           # RAG system tests
│   │   │   ├── test_services/      # Service layer tests
│   │   │   └── test_evaluation/    # Evaluation tests
│   │   ├── integration/            # Integration tests
│   │   ├── mocks/                  # Mock implementations
│   │   └── conftest.py             # Pytest configuration
│   ├── requirements.txt             # Python dependencies
│   ├── app.py                       # Flask application entry point
│   └── entrypoint.sh                # Docker entrypoint script
├── frontend/
│   ├── src/
│   │   ├── components/              # Reusable Vue components
│   │   ├── pages/                   # Main application pages
│   │   │   ├── Chatbot.vue         # Main chat interface
│   │   │   ├── Admin.vue           # Admin management panel
│   │   │   └── Login.vue           # Admin login page
│   │   ├── router/                  # Vue Router configuration
│   │   └── utils/                   # Frontend utilities
│   ├── tests/                       # Frontend tests
│   ├── package.json                 # Node.js dependencies
│   └── vitest.config.js             # Vitest configuration
├── data/                            # Application data directory (git-ignored)
│   └── knowledge_base/
│       ├── documents/               # PDF source documents
│       ├── scraped_content/         # Web-scraped UNSW handbook data
│       ├── vector_store/            # ChromaDB database files
│       └── logs/                    # Chat logs and analytics
├── docker-compose.yml               # Docker production configuration
├── run-all-tests.sh                 # Unified test runner script
├── DOCKER_README.md                 # Detailed Docker setup guide
└── README.md                        # This file
```

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- A Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))

### Option 1: Docker Deployment (Recommended)

**1. Clone the repository**

```bash
git clone <repository-url>
cd capstone-project-25t2-9900-f10a-almond
```

**2. Configure environment variables**

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your-google-gemini-api-key
ADMIN_EMAIL=admin@unsw.edu.au
ADMIN_PASSWORD=your-secure-password
SECRET_KEY=your-flask-secret-key
```

**3. Build and start containers**

```bash
docker compose up --build -d
```

**4. Wait for the backend to be ready**

```bash
docker logs chatbot-backend -f
# Wait until you see: "Running on http://0.0.0.0:5000"
```

**5. Build the knowledge base (required on first run)**

```bash
curl -X POST http://localhost:3001/api/admin/vector-store/rebuild \
  -H "Authorization: Bearer $(curl -s -X POST http://localhost:3001/api/admin/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"admin@unsw.edu.au","password":"your-secure-password"}' \
    | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')"
```

Or use the Admin Panel UI (see Workflow section below).

**6. Access the application**

| Service | URL |
|---------|-----|
| Chat Interface | http://localhost:8080 |
| Admin Panel | http://localhost:8080/admin |
| Backend API (direct) | http://localhost:3001 |

> **Note**: The backend listens internally on port 5000, mapped to host port **3001** by Docker.

---

### Option 2: Manual Development Setup

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_API_KEY="your-google-api-key"
export ADMIN_EMAIL="admin@unsw.edu.au"
export ADMIN_PASSWORD="secure-password"
export SECRET_KEY="your-secret-key"

# Run Flask development server
python app.py
```

#### Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000
npm run build    # Production build
```

---

## Workflow Guide

### First-Time Deployment

```
1. Create .env file with GOOGLE_API_KEY and admin credentials
2. docker compose up --build -d
3. Monitor startup: docker logs chatbot-backend -f
4. Open http://localhost:8080/admin → log in
5. Admin Panel → Vector Store → "Force Rebuild Knowledge Base"
6. Wait for rebuild to complete (~2–5 min depending on document count)
7. Chat at http://localhost:8080
```

### Knowledge Base Management

| Action | How |
|--------|-----|
| Add a PDF | Admin Panel → Files → Upload, **or** copy to `data/knowledge_base/documents/` then rebuild |
| Delete a PDF | Admin Panel → Files → Delete (auto-triggers vector store update) |
| Full rebuild | Admin Panel → Vector Store → Force Rebuild |
| Incremental update | Happens automatically after Admin Panel upload/delete |

### Content Scraping Workflow

```
Admin Panel → Scraping
  → Enter a UNSW URL (e.g. https://www.handbook.unsw.edu.au/...)
  → Click "Discover Links"
  → Review discovered URLs
  → Click "Confirm & Scrape"
  → Vector store updates automatically
```

### Day-to-Day Development

| Change | Action needed |
|--------|--------------|
| Modify backend Python code | None — backend volume is bind-mounted; changes apply immediately (dev mode) |
| Modify `requirements.txt` | `docker compose up --build` |
| Modify frontend Vue code | `docker compose up --build` |
| Modify environment variables | Edit `.env` → `docker compose up -d` (no rebuild) |

---

## Gemini API Quota Reference

The embedding model runs **locally** (sentence-transformers) — no API quota consumed.

| Usage | Model | Free Tier Limit |
|-------|-------|-----------------|
| Chat / Q&A generation | gemini-2.5-flash | ~20 requests/day |
| PDF chunk summarisation | gemini-1.5-flash | 1,500 requests/day |
| Embeddings | all-MiniLM-L6-v2 (local) | Unlimited |

> If you hit a 429 rate-limit error during chat, you have exhausted the free-tier daily quota for gemini-2.5-flash. Consider upgrading to a paid API key or switching to `gemini-1.5-flash` via the `GEMINI_MODEL` environment variable.

---

## Key Features

### Advanced RAG Pipeline (LangGraph)

The query processing pipeline is implemented as a LangGraph state machine with the following nodes:

```
safety_check → query_rewrite → hyde_expansion
    → hybrid_retrieve → cross_encoder_rerank
    → crag_grade → generate → hallucination_check
```

- **Safety check**: rejects off-topic or harmful queries upfront
- **Query rewrite**: expands ambiguous queries for better recall
- **HyDE**: generates a hypothetical answer to anchor embedding search
- **Hybrid retrieve**: semantic (ChromaDB) + keyword (BM25) with score fusion
- **Cross-encoder rerank**: scores (query, chunk) pairs; promotes relevant, demotes noise
- **CRAG grade**: filters chunks below relevance threshold before generation
- **Hallucination check**: validates response is grounded in retrieved context

### Hybrid Search Technology

- **Semantic Search**: ChromaDB + local sentence-transformers embeddings
- **Keyword Search**: BM25 for exact term matching
- **Score Fusion**: reciprocal rank fusion combines both signals
- **Reranking**: cross-encoder re-scores top-k results

### Content Management

- **PDF Processing**: PyMuPDF parsing with Gemini-generated contextual chunk prefixes
- **Web Scraping**: Selenium + BeautifulSoup targeting UNSW handbook
- **Incremental Updates**: new documents added to vector store without full rebuild
- **Admin Interface**: upload PDFs, manage scraped URLs, view analytics

### User Interface

- **Responsive Design**: dark/light theme, mobile-optimised
- **Typewriter Effect**: animated bot responses with loading indicators
- **Feedback System**: thumbs up/down ratings per message
- **Admin Dashboard**: query logs, file management, scraping controls

---

## API Endpoints

### Public

```
POST /api/query
Body: {"question": "What is COMP9900?", "session_id": "unique_session_id"}
Returns: {"answer": "...", "session_id": "...", "status": "answered|unanswered"}

POST /api/feedback
Body: {"session_id": "...", "feedback_type": "positive", "timestamp": "..."}

GET /docs/<filename>
Returns: PDF document files
```

### Admin (Bearer token required)

```
POST /api/admin/login
Body: {"email": "...", "password": "..."}
Returns: {"token": "jwt_token", ...}

GET  /api/admin/health
GET  /api/admin/stats
POST /api/admin/upload             (multipart PDF)
GET  /api/admin/files
DELETE /api/admin/delete/<filename>
GET  /api/admin/queries
POST /api/admin/update-query
DELETE /api/admin/delete-query/<hash>
GET  /api/admin/chat-logs
DELETE /api/admin/clear-all-logs
GET  /api/admin/vectorstore/status
GET  /api/admin/vectorstore/stats
POST /api/admin/vector-store/rebuild
POST /api/admin/scrapers/discover
POST /api/admin/scrapers/confirm-and-scrape
GET  /api/admin/scrapers/progress/<scraping_id>
POST /api/admin/scrapers/cancel/<scraping_id>
```

---

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key | `AIza...` |
| `ADMIN_EMAIL` | Admin login email | `admin@unsw.edu.au` |
| `ADMIN_PASSWORD` | Admin login password | `SecurePass123!` |
| `SECRET_KEY` | Flask session secret key | `your-secret-key-here` |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_DEBUG` | Enable Flask debug mode | `False` |
| `HOST` | Backend host address | `0.0.0.0` |
| `PORT` | Backend internal port | `5000` |
| `EMBEDDING_MODEL` | HuggingFace sentence-transformers model name | `all-MiniLM-L6-v2` |
| `GEMINI_MODEL` | Gemini model for chat/generation | `gemini-2.5-flash` |

> **Tip**: Set `EMBEDDING_MODEL=all-mpnet-base-v2` for higher-quality embeddings at the cost of slightly more RAM and slower first-start.

### Key Dependencies

**Backend (Python 3.12+)**:
- Flask 3.1+ — web framework
- google-generativeai — Gemini API client
- langchain 0.3+ / langgraph — RAG orchestration
- chromadb 1.0+ — vector database
- sentence-transformers — local embedding model
- rank-bm25 — keyword search
- crossencoder (sentence-transformers) — reranking
- selenium / beautifulsoup4 — web scraping
- PyMuPDF — PDF processing
- ragas — RAG evaluation

**Frontend (Node.js 18+)**:
- Vue 3.5+ — JavaScript framework
- Element Plus 2.10+ — UI components
- Vite 5.4+ — build tool
- markdown-it — Markdown rendering

---

## Development & Testing

### Running Tests

```bash
# All tests (backend + frontend)
./run-all-tests.sh

# Backend only
./run-all-tests.sh backend

# Frontend only
./run-all-tests.sh frontend

# With coverage reports
./run-all-tests.sh coverage
```

### Manual API Testing

```bash
# Chat query (Docker)
curl -X POST http://localhost:3001/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the prerequisites for COMP9900?", "session_id": "test_123"}'

# Admin login
curl -X POST http://localhost:3001/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@unsw.edu.au", "password": "your-password"}'

# Health check
curl http://localhost:3001/api/admin/health
```

### Test Coverage

- **Backend**: 209 test functions — AI modules, RAG pipeline, services, API endpoints
- **Frontend**: component tests, auth utilities, integration flows

---

## Troubleshooting

**Google API key invalid or missing**
- Ensure `GOOGLE_API_KEY` is set in `.env` and the key has Gemini API access enabled.

**Vector store empty after first start**
- The knowledge base is NOT automatically rebuilt on startup. Go to Admin Panel → Vector Store → Force Rebuild.

**ChromaDB "readonly database" error**
- Restart the Docker container: `docker compose restart backend`
- If it persists, delete `data/knowledge_base/vector_store/` and rebuild.

**HuggingFace model download slow on first start**
- The embedding model (~90 MB) is downloaded once and cached in a Docker volume (`huggingface_cache`). Subsequent starts are instant.

**Gemini 429 Rate Limit**
- You have hit the free-tier daily quota for gemini-2.5-flash (~20 req/day). Options:
  - Wait for quota reset (midnight Pacific Time)
  - Use a paid API key
  - Set `GEMINI_MODEL=gemini-1.5-flash` in `.env` (1500 req/day free)

**Port 3001 already in use**
- Change the host port in `docker-compose.yml`: `"3002:5000"`, then restart.

**Port 8080 already in use**
- Change the host port in `docker-compose.yml`: `"8081:80"`, then restart.

**Backend container keeps restarting**
```bash
docker logs chatbot-backend --tail 50
```
Common causes: missing `GOOGLE_API_KEY`, Python dependency error, or ChromaDB corruption.

---

## Performance & Analytics

The Admin Panel provides:

- **Response Time Tracking** — average query processing latency
- **Query Analytics** — popular topics and search patterns
- **User Feedback** — positive/negative rating breakdown
- **Vector Store Stats** — document count, chunk count, index health

Access at http://localhost:8080/admin after logging in.

---

## License

COMP9900 Capstone Project — Academic Use Only
University of New South Wales — Computer Science & Engineering

---

**Built for UNSW CSE Open Day** — Helping prospective students discover opportunities in computer science and engineering at UNSW Sydney.
