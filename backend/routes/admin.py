# routes/admin.py
import os
import sys
import subprocess
from flask import Blueprint, request, jsonify, make_response
from flask_cors import cross_origin
from datetime import datetime, timedelta
from services.auth import require_admin, create_admin_token, verify_admin_credentials
from services.log_store import load_all_chat_logs
from services.export_chatlog import export_chat_logs
from services.scraped_content_manager import ScrapedContentManager
from werkzeug.utils import secure_filename
from services.log_store import load_all_chat_logs, update_chat_log_with_admin_response, delete_chat_log_by_id

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/api/admin")

# Import centralized path configuration
from config.paths import PathConfig

DOCS_FOLDER = str(PathConfig.DOCUMENTS_DIR)
SCRAPED_CONTENT_FOLDER = str(PathConfig.SCRAPED_CONTENT_FILES_DIR)


# ========== Auth ==========
@admin_bp.route('/login', methods=['POST'])
@cross_origin()
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if verify_admin_credentials(email, password):
        token = create_admin_token()
        return jsonify({
            "token": token,
            "message": "Login successful",
            "expires_in": "1 hour"
        }), 200
    return jsonify({"error": "Invalid credentials"}), 401

@admin_bp.route('/verify-token', methods=['GET'])
@require_admin
def verify_token():
    return jsonify({
        "valid": True,
        "message": "Token is valid",
        "role": "admin"
    }), 200

# ========== Admin API ==========
@admin_bp.route('/upload', methods=['POST'])
@require_admin
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    filename = secure_filename(file.filename)
    if filename == '':
        return jsonify({"error": "Invalid filename"}), 400

    # Validate file type
    if not filename.lower().endswith('.pdf'):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    file_path = os.path.join(DOCS_FOLDER, filename)
    file.save(file_path)
    print(f"[UPLOAD] Saved file to: {file_path}")
    
    # Automatically update vector store after successful upload
    vector_updated = False
    vector_error = None
    try:
        from rag import update_knowledge_base
        # Use the same directory constant as defined in rag module
        update_knowledge_base(include_scraped=True)
        vector_updated = True
        print(f"[UPLOAD] Vector store updated successfully after uploading {filename}")
    except Exception as e:
        vector_error = str(e)
        print(f"[UPLOAD] Vector store update failed: {e}")
    
    response_data = {
        "message": "File uploaded successfully",
        "filename": filename,
        "vector_store_updated": vector_updated
    }
    
    if vector_error:
        response_data["vector_store_error"] = vector_error
    
    return jsonify(response_data), 200

@admin_bp.route('/files', methods=['GET'])
def list_files():
    files = []
    
    # Add PDF files from docs folder
    if os.path.exists(DOCS_FOLDER):
        for filename in os.listdir(DOCS_FOLDER):
            if filename.endswith(".pdf"):
                files.append({
                    "name": filename,
                    "url": f"/docs/{filename}",
                    "type": "pdf"
                })    
   
    return jsonify(files)

@admin_bp.route('/delete/<path:filename>', methods=['DELETE'])
@require_admin
def delete_file(filename):
    file_path = os.path.join(DOCS_FOLDER, filename)
    print("Trying to delete:", file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"[DELETE] Removed file: {file_path}")
        
        # Automatically update vector store after successful deletion
        vector_updated = False
        vector_error = None
        try:
            from rag import update_knowledge_base
            update_knowledge_base(include_scraped=True)
            vector_updated = True
            print(f"[DELETE] Vector store updated successfully after deleting {filename}")
        except Exception as e:
            vector_error = str(e)
            print(f"[DELETE] Vector store update failed: {e}")
        
        response_data = {
            "message": f"{filename} deleted",
            "filename": filename,
            "vector_store_updated": vector_updated
        }
        
        if vector_error:
            response_data["vector_store_error"] = vector_error
        
        return jsonify(response_data), 200
    return jsonify({"error": "File not found"}), 404

@admin_bp.route('/chatlog', methods=['GET'])
@require_admin
def export_chat_log():
    data = export_chat_logs()
    response = make_response(jsonify(data))
    response.headers['Content-Disposition'] = 'attachment; filename=chatlogs.json'
    response.headers['Content-Type'] = 'application/json'
    return response

@admin_bp.route('/unanswered', methods=['GET'])
@require_admin
def get_unanswered():
    logs = load_all_chat_logs()
    # 排除统计记录，只显示真实的未回答查询
    unanswered = [log for log in logs if not log.get("ai_answered") and log.get("type") != "stats_summary"]
    unanswered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return jsonify({
        "total": len(unanswered),
        "unanswered": unanswered
    }), 200

@admin_bp.route('/history/<session_id>', methods=['GET'])
@require_admin
def get_session_history(session_id):
    logs = load_all_chat_logs()
    # 排除统计记录，只显示真实的对话历史
    history = [log for log in logs if log.get("session_id") == session_id and log.get("type") != "stats_summary"]
    history.sort(key=lambda x: x.get("timestamp", ""))
    return jsonify({
        "session_id": session_id,
        "count": len(history),
        "history": history
    }), 200

@admin_bp.route('/export', methods=['GET'])
@require_admin
def export_data():
    data = export_chat_logs()
    return jsonify(data), 200

@admin_bp.route('/stats', methods=['GET'])
@require_admin
def get_stats():
    logs = load_all_chat_logs()
    # 排除统计记录，只统计真实查询
    query_logs = [log for log in logs if log.get("type") != "stats_summary"]
    total = len(query_logs)
    answered = len([log for log in query_logs if log.get("ai_answered")])
    unanswered = total - answered

    # Daily breakdown (排除统计记录)
    day_counts = {}
    for log in query_logs:
        ts = log.get("timestamp", "")
        if ts:
            try:
                date = datetime.fromisoformat(ts.replace('Z', '+00:00')).date().isoformat()
                day_counts[date] = day_counts.get(date, 0) + 1
            except:
                continue
    daily = [{"date": d, "count": c} for d, c in sorted(day_counts.items())]

    return jsonify({
        "total_logs": total,
        "answered": answered,
        "unanswered": unanswered,
        "daily_trends": daily
    }), 200

# (NEW) modify the answers
@admin_bp.route('/queries', methods=['GET'])
@require_admin
def get_queries():
    """
    Get the queries that need to be processed (unanswered questions + negative feedback)
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        query_type = request.args.get('type', 'all')  # all, unanswered, negative
        
        all_logs = load_all_chat_logs()
        # 排除统计记录
        real_logs = [log for log in all_logs if log.get("type") != "stats_summary"]
        filtered_logs = []
        
        if query_type == 'unanswered':
            filtered_logs = [log for log in real_logs if not log.get("ai_answered")]
        elif query_type == 'negative':
            filtered_logs = [log for log in real_logs if log.get("user_feedback") == "negative"]
        else:  # all
            filtered_logs = [
                log for log in real_logs 
                if not log.get("ai_answered") or log.get("user_feedback") == "negative"
            ]

        filtered_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        total = len(filtered_logs)
        start = (page - 1) * limit
        end = start + limit
        page_queries = filtered_logs[start:end]

        formatted_queries = []
        for log in page_queries:
            query_item = {
                "id": log.get("message_id"),
                "question": log.get("question"),
                "answer": log.get("answer"),
                "answered": log.get("ai_answered", False),
                "timestamp": log.get("timestamp"),
                "session_id": log.get("session_id"),
                "status": log.get("status"),
                "user_feedback": log.get("user_feedback"),
                "feedback_time": log.get("feedback_time"),
                "admin_answered": log.get("admin_answered", False),
                "admin_response_time": log.get("admin_response_time"),
                "matched_files": log.get("matched_files", []),
                "safety_blocked": log.get("safety_blocked", False),
                "needs_attention_reason": []
            }
            
            if not log.get("ai_answered"):
                query_item["needs_attention_reason"].append("unanswered")
            if log.get("user_feedback") == "negative":
                query_item["needs_attention_reason"].append("negative_feedback")
            if log.get("safety_blocked"):
                query_item["needs_attention_reason"].append("safety_blocked")
            
            formatted_queries.append(query_item)
        
        return jsonify({
            "queries": formatted_queries,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 0,
            "query_type": query_type
        }), 200
        
    except Exception as e:
        print(f"Error fetching queries: {str(e)}")
        return jsonify({"error": "Failed to fetch queries"}), 500


@admin_bp.route('/update-query', methods=['POST'])
@require_admin
def update_query():

    try:
        data = request.get_json()
        message_id = data.get("id")
        new_answer = data.get("answer")
        action_type = data.get("type", "update")  

        if not message_id or not new_answer:
            return jsonify({"error": "Missing message ID or answer"}), 400

        logs = load_all_chat_logs()
        original_log = None
        for log in logs:
            if log.get("message_id") == message_id:
                original_log = log
                break
        
        if not original_log:
            return jsonify({"error": "Message not found"}), 404

        action_reasons = []
        if not original_log.get("ai_answered"):
            action_reasons.append("answering unanswered question")
        if original_log.get("user_feedback") == "negative":
            action_reasons.append("updating negative feedback")
        
        print(f"Updating message {message_id} - Reasons: {', '.join(action_reasons)}")
        print(f"New answer: {new_answer[:100]}...")

        success = update_chat_log_with_admin_response(message_id, new_answer)
        
        if not success:
            return jsonify({"error": "Failed to update message"}), 500

        return jsonify({
            "message": "Query updated successfully",
            "message_id": message_id,
            "action_reasons": action_reasons
        }), 200
        
    except Exception as e:
        print(f"Error updating query: {str(e)}")
        return jsonify({"error": "Failed to update query"}), 500
    
@admin_bp.route('/delete-query/<message_id>', methods=['DELETE'])
@require_admin
def delete_query(message_id):
    try:
        success = delete_chat_log_by_id(message_id)
        
        if success:
            return jsonify({"message": "Query deleted successfully"}), 200
        else:
            return jsonify({"error": "Query not found"}), 404
        
    except Exception as e:
        print(f"Error deleting query: {str(e)}")
        return jsonify({"error": "Failed to delete query"}), 500
    
    
@admin_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "admin_query_service",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


# ========== Scrapers Management ==========
@admin_bp.route('/scrapers/status', methods=['GET'])
@require_admin
def get_scrapers_status():
    """Get comprehensive status of scrapers and content sources"""
    try:
        from scrapers.services.monitoring_service import get_scraping_status
        from rag import get_content_sources_summary
        
        # Get scraping status
        scraping_status = get_scraping_status()
        
        # Get content sources summary
        sources_summary = get_content_sources_summary()
        
        return jsonify({
            "scraping_status": scraping_status,
            "content_sources": sources_summary,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error getting scrapers status: {e}")
        return jsonify({"error": "Failed to get scrapers status"}), 500


@admin_bp.route('/scrapers/links', methods=['GET'])
@require_admin  
def get_scraper_links():
    """Get current links list from urls.txt file"""
    try:
        from scrapers.utils.file_utils import load_links_from_file
        from scrapers.config import config
        
        links = load_links_from_file()
        
        # Categorize links
        categorized = {"programs": [], "specialisations": [], "courses": [], "other": []}
        for url in links:
            if "/programs/" in url:
                categorized["programs"].append(url)
            elif "/specialisations/" in url:
                categorized["specialisations"].append(url)
            elif "/courses/" in url:
                categorized["courses"].append(url)
            else:
                categorized["other"].append(url)
        
        return jsonify({
            "links": links,
            "categorized": categorized,
            "total_count": len(links),
            "urls_file": config.URLS_FILE
        }), 200
        
    except Exception as e:
        print(f"Error getting scraper links: {e}")
        return jsonify({"error": "Failed to get scraper links"}), 500


@admin_bp.route('/scrapers/links', methods=['POST'])
@require_admin
def update_scraper_links():
    """Update links list in urls.txt file"""
    try:
        from scrapers.utils.file_utils import save_links_to_file
        from scrapers.config import config
        
        data = request.get_json()
        links = data.get("links", [])
        
        if not isinstance(links, list):
            return jsonify({"error": "Links must be provided as a list"}), 400
        
        # Validate URLs
        valid_links = []
        for link in links:
            if isinstance(link, str) and link.strip() and link.startswith("http"):
                valid_links.append(link.strip())
        
        # Convert to format expected by save_links_to_file
        categorized_links = {"programs": [], "specialisations": [], "courses": [], "other": []}
        for url in valid_links:
            if "/programs/" in url:
                categorized_links["programs"].append(url)
            elif "/specialisations/" in url:
                categorized_links["specialisations"].append(url)
            elif "/courses/" in url:
                categorized_links["courses"].append(url)
            else:
                categorized_links["other"].append(url)
        
        # Save to file
        save_links_to_file(categorized_links)
        
        return jsonify({
            "message": "Links updated successfully",
            "total_links": len(valid_links),
            "categories": {k: len(v) for k, v in categorized_links.items()}
        }), 200
        
    except Exception as e:
        print(f"Error updating scraper links: {e}")
        return jsonify({"error": "Failed to update scraper links"}), 500


@admin_bp.route('/scrapers/discover', methods=['POST'])
@require_admin
def discover_links():
    """Discover links and return preview for admin review"""
    try:
        from scrapers.services.discovery_service import discover_cse_links_with_preview
        from scrapers.utils.file_utils import load_links_from_file
        
        data = request.get_json()
        root_url = data.get("root_url", "https://www.handbook.unsw.edu.au/browse/By%20Area%20of%20Interest/InformationTechnology")
        
        # Get existing links
        existing_urls = set()
        try:
            existing_urls = set(load_links_from_file())
        except:
            existing_urls = set()
        
        # Run discovery with preview
        discovery_result = discover_cse_links_with_preview(root_url, existing_urls)
        
        return jsonify({
            "success": True,
            "root_url": root_url,
            "discovery_summary": {
                "total_links": discovery_result["total_links"],
                "new_links": discovery_result["new_links_count"],
                "existing_links": discovery_result["existing_links_count"],
                "categories": discovery_result["categories"]
            },
            "new_links_preview": discovery_result["new_links_preview"],
            "quality_check": discovery_result["quality_check"],
            "full_discovery_data": discovery_result["all_links"]  # For saving after confirmation
        }), 200
        
    except Exception as e:
        print(f"Error during link discovery: {e}")
        return jsonify({
            "success": False, 
            "error": f"Failed to discover links: {str(e)}"
        }), 500


@admin_bp.route('/scrapers/confirm-and-scrape', methods=['POST'])
@require_admin
def confirm_and_scrape():
    """Confirm discovered links and start scraping"""
    try:
        from scrapers.utils.file_utils import save_links_to_file
        from scrapers.services.scraping_service import start_scraping_with_progress
        
        data = request.get_json()
        confirmed_links = data.get("confirmed_links", [])
        auto_update_vector_store = data.get("update_vector_store", True)
        
        if not confirmed_links:
            return jsonify({
                "success": False,
                "error": "No links provided for scraping"
            }), 400
        
        # Save confirmed links to urls.txt
        save_links_to_file(confirmed_links)
        
        # Start scraping with progress tracking
        scraping_id = start_scraping_with_progress(
            confirmed_links, 
            auto_update_vector_store=auto_update_vector_store
        )
        
        return jsonify({
            "success": True,
            "message": "Scraping started successfully",
            "scraping_id": scraping_id,
            "total_urls": len(confirmed_links),
            "progress_endpoint": f"/api/admin/scrapers/progress/{scraping_id}"
        }), 200
        
    except Exception as e:
        print(f"Error starting scraping: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to start scraping: {str(e)}"
        }), 500


@admin_bp.route('/scrapers/progress/<scraping_id>', methods=['GET'])
@require_admin
def get_scraping_progress(scraping_id):
    """Get real-time scraping progress"""
    try:
        from scrapers.services.scraping_service import get_scraping_progress
        
        progress = get_scraping_progress(scraping_id)
        
        if progress is None:
            return jsonify({
                "success": False,
                "error": "Scraping session not found"
            }), 404
            
        return jsonify({
            "success": True,
            "progress": progress
        }), 200
        
    except Exception as e:
        print(f"Error getting scraping progress: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to get progress"
        }), 500


@admin_bp.route('/scrapers/cancel/<scraping_id>', methods=['POST'])
@require_admin
def cancel_scraping(scraping_id):
    """Cancel ongoing scraping operation"""
    try:
        from scrapers.services.scraping_service import cancel_scraping_session
        
        result = cancel_scraping_session(scraping_id)
        
        return jsonify({
            "success": True,
            "message": "Scraping cancelled successfully",
            "cancelled": result
        }), 200
        
    except Exception as e:
        print(f"Error cancelling scraping: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to cancel scraping"
        }), 500


@admin_bp.route('/scrapers/scrape', methods=['POST'])
@require_admin
def trigger_scraping():
    """Legacy endpoint - redirects to new workflow"""
    return jsonify({
        "message": "Please use the new interactive workflow",
        "workflow": "Use /scrapers/discover first, then /scrapers/confirm-and-scrape",
        "deprecated": True
    }), 200


@admin_bp.route('/scrapers/monitor', methods=['POST'])
@require_admin
def run_monitoring():
    """Run monitoring to check for changes and optionally auto-scrape"""
    try:
        from scrapers.services.monitoring_service import monitor_and_scrape
        
        data = request.get_json()
        auto_scrape = data.get("auto_scrape", False)
        
        result = monitor_and_scrape(auto_scrape=auto_scrape)
        
        return jsonify({
            "message": "Monitoring completed",
            "result": result
        }), 200
        
    except Exception as e:
        print(f"Error during monitoring: {e}")
        return jsonify({"error": "Failed to run monitoring"}), 500


@admin_bp.route('/vector-store/rebuild', methods=['POST'])
@require_admin
def rebuild_vector_store():
    """Force rebuild of vector store with all content"""
    try:
        from rag import force_rebuild_knowledge_base
        
        success = force_rebuild_knowledge_base(include_scraped=True)
        
        if success:
            return jsonify({
                "message": "Vector store rebuilt successfully"
            }), 200
        else:
            return jsonify({
                "error": "Vector store rebuild failed"
            }), 500
            
    except Exception as e:
        print(f"Error rebuilding vector store: {e}")
        return jsonify({"error": "Failed to rebuild vector store"}), 500


# ========== Discovery & Scraping ==========
@admin_bp.route('/discover', methods=['POST'])
@require_admin
def run_discovery():
    """Run link discovery and return discovered links"""
    try:
        # Import here to avoid import errors
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from scrapers.services.discovery_service import discover_and_save_cse_links
        from scrapers.config import config
        
        # Ensure directories exist
        config.ensure_directories()
        
        print(f"🔍 Starting link discovery...")
        links = discover_and_save_cse_links()
        
        # Prepare response data
        response_data = {
            "success": True,
            "message": "Discovery completed successfully",
            "links": links,
            "summary": {
                "programs": len(links.get('programs', [])),
                "double_degrees": len(links.get('double_degrees', [])),
                "specialisations": len(links.get('specialisations', [])),
                "courses": len(links.get('courses', [])),
                "total": sum(len(v) for v in links.values())
            }
        }
        
        print(f"✅ Discovery completed: {response_data['summary']['total']} links found")
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@admin_bp.route('/scrape', methods=['POST'])
@require_admin
def scrape_content():
    """Run content scraping for discovered links"""
    try:
        # Import here to avoid import errors
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from scrapers.services.monitoring_service import get_new_links, update_scraping_metadata
        from scrapers.services.scraping_service import scrape_urls_batch
        from scrapers.config import config
        
        # Ensure directories exist
        config.ensure_directories()
        
        # Get URLs that need scraping
        new_urls = get_new_links()
        
        if not new_urls:
            return jsonify({
                "success": True,
                "message": "No new URLs to scrape. All content is up to date.",
                "scraped_count": 0,
                "total_urls": 0
            }), 200
        
        print(f"📋 Found {len(new_urls)} URLs to scrape")
        
        # Scrape URLs
        print(f"🚀 Starting content scraping...")
        documents = scrape_urls_batch(new_urls, save_content=True)
        
        # Get successful URLs
        successful_urls = [doc.metadata["source"] for doc in documents]
        
        # Update metadata
        update_scraping_metadata(successful_urls)
        
        response_data = {
            "success": True,
            "message": "Scraping completed successfully",
            "scraped_count": len(successful_urls),
            "total_urls": len(new_urls),
            "failed_count": len(new_urls) - len(successful_urls)
        }
        
        print(f"✅ Scraping completed: {len(successful_urls)}/{len(new_urls)} successful")
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ========== Content Management (New ScrapedContentManager Integration) ==========
@admin_bp.route('/content/status', methods=['GET'])
@require_admin
def get_content_status():
    """Get comprehensive status of scraped content"""
    try:
        manager = ScrapedContentManager()
        status = manager.get_content_status()
        
        return jsonify({
            "success": True,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error getting content status: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to get content status: {str(e)}"
        }), 500

@admin_bp.route('/content/links', methods=['POST'])
@require_admin
def add_content_links():
    """Add new links for scraping"""
    try:
        data = request.get_json()
        urls = data.get("urls", [])
        auto_update_vector_store = data.get("auto_update_vector_store", True)
        
        if not urls:
            return jsonify({
                "success": False,
                "error": "No URLs provided"
            }), 400
        
        manager = ScrapedContentManager()
        result = manager.add_links(urls, auto_update_vector_store)
        
        return jsonify({
            "success": result["success"],
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }), 200 if result["success"] else 400
        
    except Exception as e:
        print(f"Error adding content links: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to add links: {str(e)}"
        }), 500

@admin_bp.route('/content/links', methods=['DELETE'])
@require_admin
def remove_content_links():
    """Remove links and their associated content"""
    try:
        data = request.get_json()
        urls = data.get("urls", [])
        update_vector_store = data.get("update_vector_store", True)
        
        if not urls:
            return jsonify({
                "success": False,
                "error": "No URLs provided"
            }), 400
        
        manager = ScrapedContentManager()
        result = manager.remove_links(urls, update_vector_store)
        
        return jsonify({
            "success": result["success"],
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error removing content links: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to remove links: {str(e)}"
        }), 500

@admin_bp.route('/content/links', methods=['PUT'])
@require_admin
def update_content_links():
    """Update/re-scrape existing links"""
    try:
        data = request.get_json()
        urls = data.get("urls")  # None = update all
        auto_update_vector_store = data.get("auto_update_vector_store", True)
        
        manager = ScrapedContentManager()
        result = manager.update_links(urls, auto_update_vector_store)
        
        return jsonify({
            "success": result["success"],
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }), 200 if result["success"] else 400
        
    except Exception as e:
        print(f"Error updating content links: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to update links: {str(e)}"
        }), 500

@admin_bp.route('/content/scraping/<scraping_id>', methods=['GET'])
@require_admin
def get_content_scraping_status(scraping_id):
    """Get status of ongoing scraping operation"""
    try:
        manager = ScrapedContentManager()
        status = manager.get_scraping_status(scraping_id)
        
        if status is None:
            return jsonify({
                "success": False,
                "error": "Scraping session not found"
            }), 404
        
        return jsonify({
            "success": True,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error getting scraping status: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to get scraping status: {str(e)}"
        }), 500

@admin_bp.route('/content/cleanup', methods=['POST'])
@require_admin
def cleanup_orphaned_content():
    """Clean up orphaned content files and vector store entries"""
    try:
        manager = ScrapedContentManager()
        result = manager.cleanup_orphaned_content()
        
        return jsonify({
            "success": result["success"],
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error cleaning up content: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to cleanup content: {str(e)}"
        }), 500


# ========== Error handlers ==========
@admin_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Admin endpoint not found'}), 404

@admin_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
