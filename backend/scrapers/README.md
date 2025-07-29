# UNSW Handbook Scrapers Module

A refactored web scraping module with clear separation of concerns, supporting link discovery, content extraction, and unified RAG vectorization.

## 📁 Module Structure

```
scrapers/
├── __init__.py              # Module entry point
├── link_discovery.py        # Link discovery functionality
├── page_scraper.py          # Single page content extraction
├── monitor.py               # Link change monitoring
├── config.py                # Configuration management
└── README.md               # Documentation

rag/scraped_content/
├── urls.txt                 # Link list (admin editable)
├── content/                 # Page content JSON files
└── metadata.json            # Scraping metadata

scripts/
├── run_discovery.py         # Link discovery script
├── run_scraping.py          # Content scraping script
└── update_vector_store.py   # Vector store update script
```

## 🚀 Quick Start

### Admin Panel Workflow (Recommended)

1. **Navigate to Admin Panel** → Scrapers section
2. **Click "Discover Links"** → System discovers all relevant links from UNSW handbook
3. **Review Discovery Results** → Popup window shows discovered links and statistics
4. **Confirm Selection** → Click "Start Scraping" to begin content extraction
5. **Monitor Progress** → Real-time status updates in admin panel
6. **Auto Vector Store Update** → System automatically updates RAG vector store with new content

### Manual Script Execution (Development)

```bash
# Manual link discovery (development only)
python scripts/run_discovery.py

# Manual content scraping (development only)
python scripts/run_scraping.py

# Manual vector store update (development only)  
python scripts/update_vector_store.py
```

## 🔧 Module API

### Link Discovery (link_discovery.py)
```python
from scrapers.link_discovery import discover_cse_links, save_links_to_file, load_links_from_file

# Discover links
links = discover_cse_links("https://handbook.unsw.edu.au/browse/...")

# Save/load links
save_links_to_file(links)
urls = load_links_from_file()
```

### Single Page Scraping (page_scraper.py)
```python
from scrapers.page_scraper import scrape_single_page, save_page_content

# Scrape single page
doc = scrape_single_page("https://handbook.unsw.edu.au/...")

# Save content
save_page_content(doc)
```

### Monitoring Management (monitor.py)
```python
from scrapers.monitor import check_links_changed, get_new_links, get_scraping_status

# Check link changes
changed = check_links_changed()

# Get new links
new_urls = get_new_links()

# Get scraping status
status = get_scraping_status()
```

## 🌐 Admin Panel API

### Scraper Status
```
GET /api/admin/scrapers/status         # Get current scraping status and statistics
```

### Interactive Link Discovery
```
POST   /api/admin/scrapers/discover   # Discover new links, return preview with statistics
GET    /api/admin/scrapers/links      # Get current link list
POST   /api/admin/scrapers/links      # Update/save link list after confirmation
```

### Interactive Content Scraping
```
POST   /api/admin/scrapers/scrape     # Trigger content scraping with progress updates
GET    /api/admin/scrapers/progress   # Get real-time scraping progress
POST   /api/admin/scrapers/cancel     # Cancel ongoing scraping operation
```

### Automatic Vector Store Management
```
POST   /api/admin/vector-store/rebuild  # Force rebuild vector store
GET    /api/admin/vector-store/status   # Check vector store update status
```

## 📊 Workflow

### Admin Panel Interactive Workflow
1. **Admin Triggers Discovery**: Admin clicks "Discover Links" button in admin panel
2. **Discovery Results Preview**: System returns popup window with:
   - List of discovered links by category (programs, courses, specializations)
   - Statistics (total links, new links, existing links)
   - Link quality indicators
3. **Admin Review & Confirmation**: Admin reviews the discovered links and clicks "Confirm & Start Scraping"
4. **Automated Content Scraping**: System automatically:
   - Saves confirmed links to `urls.txt`
   - Triggers `page_scraper` for each new link
   - Provides real-time progress updates in admin panel
5. **Automatic RAG Integration**: System automatically updates vector store with new content

### Technical Implementation
- ✅ **Interactive Discovery**: `link_discovery.py` called via admin panel API
- ✅ **Real-time Preview**: Discovery results returned to frontend for admin review
- ✅ **Automated Scraping**: `page_scraper.py` triggered automatically after confirmation
- ✅ **Progress Tracking**: Real-time scraping status updates for admin monitoring
- ✅ **Automatic Integration**: Vector store updated automatically with new content

## 💻 Admin Panel User Interface

### Discovery Results Window
When admin clicks "Discover Links", a popup window displays:

```
📊 Link Discovery Results
========================

📍 Discovery Summary:
• Total Links Found: 487
• New Links: 23
• Existing Links: 464
• Categories: Programs (45), Courses (398), Specializations (44)

📋 Preview of New Links:
✅ https://handbook.unsw.edu.au/undergraduate/programs/2025/3799 - Data Science & Decisions
✅ https://handbook.unsw.edu.au/postgraduate/courses/2025/COMP6850 - Advanced Topics in AI
✅ https://handbook.unsw.edu.au/undergraduate/courses/2025/COMP1521 - Computer Systems Fundamentals
... (showing first 10 new links)

🔍 Quality Check:
✅ All links accessible
✅ Content structure validated
⚠️  2 links may contain duplicate content

[Cancel] [Confirm & Start Scraping]
```

### Scraping Progress Interface
After confirmation, admin panel shows real-time progress:

```
🔄 Content Scraping in Progress
===============================

📊 Progress: 15/23 completed (65%)
⏱️ Estimated Time Remaining: 2 minutes
🎯 Current: Scraping COMP6850 - Advanced Topics in AI

✅ Completed (15):
• Data Science & Decisions (3799) - 2,450 chars extracted
• Computer Systems Fundamentals (COMP1521) - 3,120 chars extracted
• ...

🔄 In Progress (1):
• Advanced Topics in AI (COMP6850) - Processing...

⏳ Pending (7):
• COMP9517, COMP6991, INFS5710, ...

📈 Statistics:
• Success Rate: 100%
• Average Content Length: 2,800 characters
• Vector Store: Auto-update scheduled

[Cancel Scraping] [View Details]
```

## 🔧 Configuration Options

Configure in `scrapers/config.py`:

```python
# Chrome settings
CHROME_OPTIONS = {
    "headless": True,
    "no_sandbox": True,
    # ...
}

# Scraping settings
PAGE_LOAD_TIMEOUT = 10
REQUEST_DELAY = 2
RETRY_ATTEMPTS = 3

# Content filtering
MIN_CONTENT_LENGTH = 50
MAX_CONTENT_LENGTH = 50000
```

## 📝 File Formats

### urls.txt Format
```txt
# UNSW CSE Handbook Links
# Auto-discovered on 2025-01-16 10:30:00
# Edit this file to add/remove links for scraping

# === PROGRAMS ===
https://www.handbook.unsw.edu.au/undergraduate/programs/2025/3782
https://www.handbook.unsw.edu.au/undergraduate/programs/2025/3778

# === SPECIALISATIONS ===
https://www.handbook.unsw.edu.au/undergraduate/specialisations/2025/COMPA1

# === COURSES ===
https://www.handbook.unsw.edu.au/undergraduate/courses/2025/COMP1511
```

### Content JSON Format
```json
{
  "page_content": "# Advanced Science (Honours) / Computer Science\n\n**Code:** 3782...",
  "metadata": {
    "source": "https://...",
    "title": "Advanced Science (Honours) / Computer Science",
    "type": "program",
    "code": "3782",
    "faculty": "Faculty of Science Faculty of Engineering",
    "content_length": 1881,
    "scraped_at": "2025-01-16T10:30:00"
  },
  "saved_at": "2025-01-16T10:30:05"
}
```

## 📋 RAG Integration

### Document Processing Strategy

The scrapers module integrates seamlessly with the RAG system:

- **PDF Documents**: Processed using spaCy for semantic sentence-based chunking
- **JSON Documents**: **Kept as complete chunks to preserve full context**
- **Vector Store**: Unified storage combining both PDF chunks and complete JSON documents

### Processing Pipeline

1. **PDF Processing**: 
   - Load documents using PyMuPDF
   - Split using spaCy sentence segmentation (3 sentences per chunk)
   - Metadata tagged as `content_type: "pdf"`

2. **JSON Processing**:
   - Load scraped JSON documents with structured markdown content
   - **Preserve as complete documents** (no chunking)
   - Metadata tagged as `content_type: "scraped_web"`

3. **Unified Vectorization**:
   - Create embeddings for all document types
   - Store in ChromaDB with proper metadata classification
   - Support efficient retrieval for both PDF chunks and complete JSON documents

## 🛠️ Troubleshooting

### Common Issues

1. **Chrome Driver Errors**
   - Ensure Chrome is installed on the system
   - Check chromedriver is in PATH

2. **Permission Errors**
   - Ensure write permissions for `rag/scraped_content/` directory

3. **Memory Issues**
   - Reduce `--max-urls` parameter
   - Use `--headless` mode

4. **Vector Store Update Failures**
   - Check Google API key configuration
   - Ensure sufficient storage space

### Debug Commands

```bash
# Check scraper status
python -c "from scrapers.monitor import get_scraping_status; print(get_scraping_status())"

# Test single page scraping
python -c "from scrapers.page_scraper import scrape_single_page; doc = scrape_single_page('URL'); print(len(doc.page_content))"

# Check vector store status
python -c "from rag import get_content_sources_summary; print(get_content_sources_summary())"
```

## 🔄 Updates and Maintenance

### Regular Maintenance Tasks

1. **Link Updates**: Periodically run link discovery to update link lists
2. **Content Sync**: Monitor link changes for incremental content scraping
3. **Vector Store Optimization**: Regularly rebuild vector store for optimal performance

### Monitoring Metrics

- Total links and category statistics
- Scraping success rate
- Content quality metrics (length, sections)
- Vector store update timestamps

## 🎯 Technical Features

- ✅ **Interactive Admin Interface**: Point-and-click workflow through admin panel with real-time feedback
- ✅ **Preview Before Action**: Discovery results shown to admin for review before scraping begins
- ✅ **Real-time Progress Tracking**: Live updates on scraping progress with detailed statistics
- ✅ **Automatic Integration**: Seamless integration with RAG vector store without manual intervention
- ✅ **Quality Optimization**: Advanced content extraction eliminating duplicates and hidden content
- ✅ **Context Preservation**: JSON documents maintained as complete chunks for comprehensive information retrieval
- ✅ **Error Resilience**: Robust error handling with automatic retries and detailed error reporting

## 🔍 Content Quality Assurance

### Content Extraction Process

1. **Structured Parsing**: Extract content using CSS selectors for consistent formatting
2. **Markdown Conversion**: Convert HTML to markdown with proper heading hierarchy
3. **Content Validation**: Filter out low-quality or insufficient content
4. **Metadata Enhancement**: Extract and preserve academic metadata (codes, faculties, etc.)

### Quality Metrics

- Minimum content length validation
- Academic structure verification (headings, sections)
- Metadata completeness checks
- Duplicate content detection and removal

## 🎊 Why This Interactive Approach?

### Benefits of Admin Panel Workflow

1. **🎛️ Full Control**: Admin has complete visibility and control over what gets scraped
2. **📊 Data Quality**: Preview and review discovered links before committing to scraping
3. **⚡ Real-time Feedback**: Immediate progress updates and error notifications
4. **🛡️ Safety First**: No unexpected automated scraping - everything requires admin approval
5. **🔄 Seamless Integration**: Automatic RAG vector store updates without manual intervention
6. **📱 User-Friendly**: No command-line knowledge required - simple point-and-click interface

### Comparison with Script-Based Approach

| Feature | Interactive Admin Panel | Manual Scripts |
|---------|------------------------|----------------|
| User Experience | ✅ Intuitive GUI | ❌ Command-line required |
| Preview Links | ✅ Before scraping | ❌ After discovery |
| Progress Tracking | ✅ Real-time updates | ❌ Terminal output only |
| Error Handling | ✅ User-friendly messages | ❌ Technical error logs |
| Control | ✅ Admin approval required | ❌ Fully automated |
| Vector Store Update | ✅ Automatic | ❌ Manual step required |

---

*Last updated: July 2025*