# UNSW CSE Open Day Chatbot

A COMP9900 capstone project providing an AI-powered chatbot for UNSW Computer Science & Engineering Open Day visitors. The system uses Retrieval-Augmented Generation (RAG) with Google Gemini 2.5 Flash to provide accurate information about UNSW CSE programs, courses, and campus facilities.

## System Overview

This chatbot combines:
- **Google Gemini 2.5 Flash** for natural language generation
- **ChromaDB** vector database for semantic document search  
- **BM25** keyword search for improved retrieval accuracy
- **Web scraping** from UNSW handbook for up-to-date course information
- **PDF processing** for campus documents and guides

## Architecture

### Backend (Python Flask)
- **Flask** web framework with CORS support
- **Google Generative AI** (`google-generativeai`) for LLM and embeddings
- **LangChain** framework for RAG pipeline orchestration
- **ChromaDB** for vector storage and similarity search
- **rank-bm25** for keyword-based search
- **Selenium + BeautifulSoup** for UNSW handbook web scraping
- **PyMuPDF** for PDF document processing
- **NLTK** for text preprocessing

### Frontend (Vue 3)
- **Vue 3** with Composition API and `<script setup>` syntax
- **Element Plus** UI component library
- **Vite** for fast development and building
- **Markdown-it** for rendering formatted bot responses
- **Vue Router** for navigation between pages

### Data Storage
- **Documents**: PDF files stored in `data/knowledge_base/documents/`
- **Scraped Content**: UNSW handbook data in `data/knowledge_base/scraped_content/`
- **Vector Store**: ChromaDB database in `data/knowledge_base/vector_store/`
- **Chat Logs**: Conversation logs in `data/knowledge_base/logs/chat_logs.jsonl`

## Project Structure

```
capstone-project-25t2-9900-f10a-almond/
├── backend/
│   ├── ai/                           # AI processing modules
│   │   ├── llm_client.py            # Google Gemini client management
│   │   ├── prompt_manager.py        # Prompt templates and engineering
│   │   ├── query_processor.py       # Query enhancement and rewriting
│   │   ├── response_generator.py    # AI response generation
│   │   └── safety_checker.py        # Content safety validation
│   ├── rag/                         # Retrieval-Augmented Generation
│   │   ├── vector_store.py          # ChromaDB operations
│   │   ├── hybrid_search.py         # Combined semantic + keyword search
│   │   ├── document_loader.py       # PDF and content processing
│   │   ├── text_splitter.py         # Intelligent text chunking
│   │   ├── chain_builder.py         # RAG pipeline construction
│   │   └── incremental_vectorstore.py # Background vector store updates
│   ├── scrapers/                    # Web content extraction
│   │   ├── services/                # Scraping service implementations
│   │   ├── core/                    # Base scraper classes and types
│   │   └── utils/                   # Scraping utilities
│   ├── services/                    # Business logic services
│   │   ├── query_processor.py       # Main query orchestration
│   │   ├── auth.py                  # Admin authentication
│   │   ├── log_store.py            # Chat logging and storage
│   │   └── export_chatlog.py       # Chat log export functionality
│   ├── routes/                      # Flask API endpoints
│   │   ├── user.py                 # Public chat endpoints
│   │   └── admin.py                # Admin management endpoints
│   ├── config/                      # Configuration management
│   │   └── paths.py                # Path configuration
│   ├── scripts/                     # Utility scripts
│   │   ├── update_vector_store.py  # Vector store management
│   │   └── full_pipeline.py        # Complete data processing pipeline
│   ├── test/                        # Testing files
│   ├── requirements.txt            # Python dependencies
│   └── app.py                      # Flask application entry point
├── frontend/
│   ├── src/
│   │   ├── components/             # Reusable Vue components
│   │   │   └── LoadingSpinner.vue # Loading animation component
│   │   ├── pages/                  # Main application pages
│   │   │   ├── Chatbot.vue        # Main chat interface
│   │   │   ├── Admin.vue          # Admin management panel
│   │   │   └── Login.vue          # Admin login page
│   │   ├── router/                 # Vue Router configuration
│   │   ├── utils/                  # Frontend utilities
│   │   │   └── auth.js            # Authentication helpers
│   │   └── assets/                 # Static assets
│   │       ├── logoDark.png       # Dark theme logo
│   │       └── logoLight.png      # Light theme logo
│   ├── package.json               # Node.js dependencies
│   └── vite.config.js             # Vite configuration
├── data/                           # Application data directory
│   └── knowledge_base/
│       ├── documents/              # PDF source documents
│       │   ├── UNSW_CSE_Labs.pdf
│       │   ├── Campus_tours___UNSW_College.pdf
│       │   └── [other PDF files...]
│       ├── scraped_content/        # Web-scraped UNSW handbook data
│       │   ├── content/            # JSON files with course information
│       │   ├── metadata.json      # Scraping metadata
│       │   └── urls.txt           # Scraped URLs list
│       ├── vector_store/           # ChromaDB database files
│       │   ├── chroma.sqlite3     # ChromaDB SQLite database
│       │   └── source_files.txt   # Source file tracking
│       └── logs/                   # Chat logs and analytics
│           └── chat_logs.jsonl    # JSONL format conversation logs
├── docker-compose.yml              # Docker production configuration
├── docker-compose.dev.yml          # Docker development configuration
├── DOCKER_README.md                # Detailed Docker setup guide
└── README.md                       # This file
```

## Quick Start

### Option 1: Docker Deployment (Recommended)

1. **Clone and setup**:
```bash
git clone <repository-url>
cd capstone-project-25t2-9900-f10a-almond
```

2. **Configure environment variables**:
```bash
# Copy the Docker environment template (if exists)
# Or create a .env file manually
nano .env
```

Add these variables to `.env`:
```env
GOOGLE_API_KEY=your-google-gemini-api-key
ADMIN_EMAIL=admin@unsw.edu.au
ADMIN_PASSWORD=your-secure-password
SECRET_KEY=your-flask-secret-key
```

3. **Start the application**:
```bash
docker-compose up -d
```

4. **Access the application**:
- **Chat Interface**: http://localhost:8080
- **Admin Panel**: http://localhost:8080/admin
- **Backend API**: http://localhost:5000

See [DOCKER_README.md](DOCKER_README.md) for comprehensive Docker setup instructions.

### Option 2: Manual Development Setup

#### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export GOOGLE_API_KEY="your-google-api-key"
export ADMIN_EMAIL="admin@unsw.edu.au"
export ADMIN_PASSWORD="secure-password"
export SECRET_KEY="your-secret-key"

# Run Flask development server
python app.py
```

#### Frontend Setup
```bash
cd frontend

# Install Node.js dependencies
npm install

# Start development server (http://localhost:3000)
npm run dev

# Build for production
npm run build
```

## Key Features

### AI Conversation Engine
- **Context-Aware Responses**: Maintains conversation history for natural follow-up questions
- **Query Enhancement**: Automatically rewrites queries for better search results  
- **Safety Filtering**: Ensures responses focus on UNSW-related content
- **Fallback Handling**: Uses direct Gemini responses when knowledge base is insufficient

### Hybrid Search Technology
- **Semantic Search**: ChromaDB with Google embeddings for contextual document retrieval
- **Keyword Search**: BM25 algorithm for exact term matching
- **Combined Scoring**: Hybrid approach balances semantic understanding with keyword relevance
- **Performance Optimization**: Response caching and similarity-based deduplication

### Content Management System
- **Automated Web Scraping**: Extracts course information from UNSW handbook
- **Document Processing**: Intelligent PDF parsing with metadata extraction
- **Vector Store Management**: Incremental updates without service interruption
- **Admin Interface**: Upload documents, manage content, view analytics

### User Interface Features
- **Modern Design**: Clean, responsive interface with dark/light theme toggle
- **Real-time Interaction**: Typewriter effect for bot responses with loading animations
- **User Feedback**: Thumbs up/down rating system and message copying
- **Mobile Optimized**: Responsive design for desktop, tablet, and mobile devices

## API Endpoints

### Public Endpoints
```
POST /api/query
Content-Type: application/json
Body: {"question": "What is COMP9900?", "session_id": "unique_session_id"}
```

```
POST /api/feedback
Content-Type: application/json
Body: {"session_id": "session_id", "feedback_type": "positive", "timestamp": "2024-01-01T00:00:00"}
```

### Admin Endpoints (Requires Authentication Token)
```
POST /api/admin/login
Body: {"email": "admin@unsw.edu.au", "password": "password"}
Returns: {"token": "jwt_token"}
```

```
GET /api/admin/health
Returns: System health status
```

```
GET /api/admin/queries?page=1&limit=20&filter=all
Returns: Paginated query logs with analytics
```

```
POST /api/admin/upload
Content-Type: multipart/form-data
Body: PDF file upload
```

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
| `PORT` | Backend port number | `5000` |

### Key Dependencies

**Backend (Python 3.12+)**:
- Flask 3.1+ - Web framework
- google-generativeai - Gemini API client
- langchain 0.3+ - RAG framework
- chromadb 1.0+ - Vector database
- rank-bm25 - Keyword search
- selenium - Web scraping
- PyMuPDF - PDF processing

**Frontend (Node.js 18+)**:
- Vue 3.5+ - JavaScript framework
- Element Plus 2.10+ - UI components
- Vite 5.4+ - Build tool
- markdown-it - Markdown rendering

## Development & Testing

### Running Tests
```bash
cd backend
python -m pytest test/ -v
```

### API Testing Examples
```bash
# Test chat functionality
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the prerequisites for COMP9900?",
    "session_id": "test_session_123"
  }'

# Check system health
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/admin/health

# Admin login
curl -X POST http://localhost:5000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@unsw.edu.au", "password": "your-password"}'
```

### Knowledge Base Management
```bash
# Update vector store with new documents
cd backend
python scripts/update_vector_store.py

# Run complete data processing pipeline
python scripts/full_pipeline.py

# Manual web scraping
python scripts/run_scraping.py
```

## Troubleshooting

### Common Issues

**1. Google API Authentication Error**
- Verify `GOOGLE_API_KEY` is correctly set
- Ensure the API key has access to Gemini API
- Check that `backend/rag/key.json` exists (if using service account)

**2. Vector Store Initialization**
- First startup may take several minutes to build the vector database
- Check logs for "Vector store initialization completed"
- Ensure sufficient disk space (minimum 1GB for full knowledge base)

**3. Port Conflicts**
- Default ports: Frontend (8080), Backend (5000)
- Change ports in `docker-compose.yml` if conflicts occur
- For manual setup, use different ports with `PORT` environment variable

**4. Memory Issues**
- Vector operations require minimum 2GB available RAM
- Monitor memory usage during vector store updates
- Consider increasing Docker memory limits if using containers

### Debug Mode
```bash
# Enable detailed logging
export FLASK_DEBUG=True
export FLASK_ENV=development

# View real-time logs
tail -f data/knowledge_base/logs/chat_logs.jsonl

# Check Docker container logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Performance & Analytics

The system tracks detailed performance metrics:
- **Response Times**: Average query processing time
- **Cache Hit Rates**: Efficiency of response caching
- **Token Usage**: Google API consumption tracking  
- **User Feedback**: Positive/negative ratings and interactions
- **Query Analytics**: Popular topics and search patterns

Access analytics through the admin panel at `/admin` after logging in.

## License

COMP9900 Capstone Project - Academic Use Only  
University of New South Wales - Computer Science & Engineering

---

**Built for UNSW CSE Open Day** - Helping prospective students discover opportunities in computer science and engineering at UNSW Sydney.