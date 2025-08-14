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
from services.log_store import load_all_chat_logs, update_chat_log_with_admin_response, delete_chat_log_by_id, clear_all_chat_logs

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
    
    # Schedule asynchronous vector store update
    from services.async_vectorstore_updater import schedule_vectorstore_update
    update_task_id = schedule_vectorstore_update(f"file_uploaded_{filename}", include_scraped=True)
    
    print(f"[UPLOAD] Scheduled async vector store update after uploading {filename} (Task ID: {update_task_id})")
    
    response_data = {
        "message": "File uploaded successfully",
        "filename": filename,
        "vector_store_update": {
            "status": "scheduled",
            "task_id": update_task_id
        }
    }
    
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
        
        # Schedule asynchronous vector store update after deletion
        from services.async_vectorstore_updater import schedule_vectorstore_update
        update_task_id = schedule_vectorstore_update(f"file_deleted_{filename}", include_scraped=True)
        
        print(f"[DELETE] Scheduled async vector store update after deleting {filename} (Task ID: {update_task_id})")
        
        response_data = {
            "message": f"{filename} deleted",
            "filename": filename,
            "vector_store_update": {
                "status": "scheduled",
                "task_id": update_task_id
            }
        }
        
        return jsonify(response_data), 200
    return jsonify({"error": "File not found"}), 404

@admin_bp.route('/vectorstore/status', methods=['GET'])
def get_vectorstore_status():
    """Get vector store update queue status"""
    from services.async_vectorstore_updater import get_vectorstore_queue_status
    status = get_vectorstore_queue_status()
    return jsonify(status), 200

@admin_bp.route('/vectorstore/status/<task_id>', methods=['GET'])
def get_vectorstore_task_status(task_id):
    """Get status of a specific vector store update task"""
    from services.async_vectorstore_updater import get_vectorstore_update_status
    status = get_vectorstore_update_status(task_id)
    
    if status:
        return jsonify(status), 200
    else:
        return jsonify({"error": "Task not found"}), 404

@admin_bp.route('/vectorstore/stats', methods=['GET'])
def get_vectorstore_stats():
    """Get vector store statistics and document counts"""
    from rag.incremental_vectorstore import get_vectorstore_stats
    stats = get_vectorstore_stats()
    return jsonify(stats), 200

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
    # Exclude stats records, only show real unanswered queries
    unanswered = [log for log in logs if not log.get("answered", log.get("ai_answered", False)) and log.get("type") != "stats_summary"]
    unanswered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return jsonify({
        "total": len(unanswered),
        "unanswered": unanswered
    }), 200

@admin_bp.route('/history/<session_id>', methods=['GET'])
@require_admin
def get_session_history(session_id):
    logs = load_all_chat_logs()
    # Exclude stats records, only show real conversation history
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
    # Exclude stats records, only count real queries
    query_logs = [log for log in logs if log.get("type") != "stats_summary"]
    total = len(query_logs)
    answered = len([log for log in query_logs if log.get("answered", log.get("ai_answered", False))])
    unanswered = total - answered

    # Calculate average response time
    response_times = [log.get("response_time_ms", 0) for log in query_logs if log.get("response_time_ms")]
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    # Calculate total tokens used
    total_tokens = sum(log.get("tokens_used", 0) for log in query_logs)
    
    # Calculate feedback statistics
    positive_feedback = len([log for log in query_logs if log.get("user_feedback") == "positive"])
    negative_feedback = len([log for log in query_logs if log.get("user_feedback") == "negative"])

    # Daily breakdown (exclude stats records)
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
        "total_queries": total,
        "answered": answered,
        "unanswered": unanswered,
        "avg_response_time_ms": round(avg_response_time, 2),
        "total_tokens": total_tokens,
        "positive_feedback": positive_feedback,
        "negative_feedback": negative_feedback,
        "daily_trends": daily
    }), 200

# (NEW) modify the answers
@admin_bp.route('/queries', methods=['GET'])
@require_admin
def get_queries():
    """
    Get all queries from cached queries (deduplicated by question_hash)
    Falls back to chat logs for legacy data
    """
    try:
        from services.cache_store import get_cache_entries_with_pagination
        
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        query_type = request.args.get('type', 'all')  # all, rag_answered, ai_answered, unanswered, negative_feedback, positive_feedback
        
        # Map query_type for filtering
        cache_query_type = None
        cache_user_feedback = None
        
        if query_type in ['rag_answered', 'ai_answered', 'unanswered']:
            cache_query_type = query_type
        elif query_type in ['negative_feedback', 'positive_feedback']:
            cache_user_feedback = query_type
        
        # Get cached queries with pagination and filtering
        cached_entries, total = get_cache_entries_with_pagination(
            page=page, 
            limit=limit, 
            query_type=cache_query_type,
            user_feedback=cache_user_feedback
        )
        
        formatted_queries = []
        for entry in cached_entries:
            # Determine query_type for display (handle legacy data)
            query_type_val = entry.get("query_type")
            if query_type_val is None:
                # Legacy data: derive query_type from answer_quality
                answer_quality = entry.get("answer_quality", "")
                if answer_quality in ["rag_answered", "admin_answered"]:
                    query_type_val = "rag_answered" if entry.get("matched_files") else "ai_answered"
                elif answer_quality == "ai_answered":
                    query_type_val = "ai_answered"
                else:
                    query_type_val = "unanswered"
            
            answered = query_type_val != "unanswered"
            
            query_item = {
                "id": entry.get("question_hash"),  # Use question_hash as ID for cache-based queries
                "question": entry.get("question"),
                "answer": entry.get("answer"),
                "answered": answered,
                "query_type": query_type_val,
                "timestamp": entry.get("updated_at", entry.get("created_at")),
                "session_id": None,  # Not relevant for cached queries
                "status": "answered" if answered else "unanswered",
                "user_feedback": entry.get("user_feedback"),
                "feedback_time": None,  # Could be derived from updated_at if needed
                "admin_answered": entry.get("answer_quality") == "admin_answered",
                "admin_response_time": entry.get("updated_at") if entry.get("answer_quality") == "admin_answered" else None,
                "matched_files": entry.get("matched_files", []),
                "safety_blocked": False,  # Not stored in cache currently
                "usage_count": entry.get("usage_count", 0),
                "last_used": entry.get("last_used"),
                "needs_attention_reason": []
            }
            
            # Add attention reasons
            if not answered:
                query_item["needs_attention_reason"].append("unanswered")
            if entry.get("user_feedback") == "negative":
                query_item["needs_attention_reason"].append("negative_feedback")
            
            formatted_queries.append(query_item)
        
        return jsonify({
            "queries": formatted_queries,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 0,
            "query_type": query_type,
            "data_source": "cached_queries"
        }), 200
        
    except Exception as e:
        print(f"Error fetching queries from cache: {str(e)}")
        return jsonify({"error": "Failed to fetch queries"}), 500


@admin_bp.route('/update-query', methods=['POST'])
@require_admin
def update_query():
    try:
        from services.cache_store import update_cached_answer
        from services.log_store import sync_cache_to_chat_logs
        
        data = request.get_json()
        question_hash = data.get("id")  # Now expecting question_hash as ID
        new_answer = data.get("answer")
        action_type = data.get("type", "update")  

        if not question_hash or not new_answer:
            return jsonify({"error": "Missing question hash or answer"}), 400

        # Update cached query first
        cache_updated = update_cached_answer(question_hash, new_answer, "admin_answered")
        
        if not cache_updated:
            return jsonify({"error": "Failed to update cached query"}), 500

        # Sync changes to all related chat logs
        sync_success = sync_cache_to_chat_logs(question_hash, new_answer=new_answer)
        
        action_reasons = ["admin updated cached query"]
        if sync_success:
            action_reasons.append("synced to related chat logs")
        else:
            action_reasons.append("warning: sync to chat logs failed")
        
        print(f"Updated cached query {question_hash} - Reasons: {', '.join(action_reasons)}")
        print(f"New answer: {new_answer[:100]}...")

        return jsonify({
            "message": "Query updated successfully",
            "question_hash": question_hash,
            "action_reasons": action_reasons,
            "cache_updated": cache_updated,
            "logs_synced": sync_success
        }), 200
        
    except Exception as e:
        print(f"Error updating query: {str(e)}")
        return jsonify({"error": "Failed to update query"}), 500
    
@admin_bp.route('/delete-query/<question_hash>', methods=['DELETE'])
@require_admin
def delete_query(question_hash):
    """
    Delete cached query only, chat logs remain for audit purposes
    """
    try:
        from services.cache_store import delete_cached_entry_by_hash
        
        success = delete_cached_entry_by_hash(question_hash)
        
        if success:
            return jsonify({
                "message": "Cached query deleted successfully",
                "question_hash": question_hash,
                "note": "Chat logs preserved for audit purposes"
            }), 200
        else:
            return jsonify({"error": "Cached query not found"}), 404
        
    except Exception as e:
        print(f"Error deleting cached query: {str(e)}")
        return jsonify({"error": "Failed to delete cached query"}), 500
    

@admin_bp.route('/chat-logs', methods=['GET'])
@require_admin
def get_chat_logs():
    """
    Get chat logs for audit purposes (read-only)
    Returns complete conversation history
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        session_id = request.args.get('session_id')
        
        all_logs = load_all_chat_logs()
        # Exclude stats records
        real_logs = [log for log in all_logs if log.get("type") != "stats_summary"]
        
        # Filter by session_id if provided
        if session_id:
            real_logs = [log for log in real_logs if log.get("session_id") == session_id]
        
        real_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        total = len(real_logs)
        start = (page - 1) * limit
        end = start + limit
        page_logs = real_logs[start:end]
        
        return jsonify({
            "chat_logs": page_logs,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 0,
            "session_filter": session_id,
            "data_source": "chat_logs",
            "read_only": True
        }), 200
        
    except Exception as e:
        print(f"Error fetching chat logs: {str(e)}")
        return jsonify({"error": "Failed to fetch chat logs"}), 500

@admin_bp.route('/clear-all-logs', methods=['DELETE'])
@require_admin
def clear_all_logs():
    """Clear all chat logs - DANGEROUS OPERATION"""
    try:
        success = clear_all_chat_logs()
        
        if success:
            return jsonify({
                "message": "All chat logs cleared successfully",
                "timestamp": datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({"error": "Failed to clear chat logs"}), 500
            
    except Exception as e:
        print(f"Error clearing all logs: {str(e)}")
        return jsonify({"error": f"Failed to clear logs: {str(e)}"}), 500
    

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
    """Get current links list from urls.txt file with pagination support"""
    try:
        from scrapers.utils.file_utils import load_links_from_file
        from scrapers.config import config
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        # Load all links
        all_links = load_links_from_file()
        total_count = len(all_links)
        
        # Calculate pagination
        start_index = (page - 1) * limit
        end_index = start_index + limit
        paginated_links = all_links[start_index:end_index]
        
        # Categorize paginated links
        categorized = {"programs": [], "specialisations": [], "courses": [], "other": []}
        for url in paginated_links:
            if "/programs/" in url:
                categorized["programs"].append(url)
            elif "/specialisations/" in url:
                categorized["specialisations"].append(url)
            elif "/courses/" in url:
                categorized["courses"].append(url)
            else:
                categorized["other"].append(url)
        
        return jsonify({
            "links": paginated_links,
            "categorized": categorized,
            "total_count": total_count,
            "current_page": page,
            "page_size": limit,
            "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 0,
            "urls_file": config.URLS_FILE
        }), 200
        
    except Exception as e:
        print(f"Error getting scraper links: {e}")
        return jsonify({"error": "Failed to get scraper links"}), 500


@admin_bp.route('/scrapers/links/<path:url>', methods=['DELETE'])
@require_admin
def delete_scraper_link(url):
    """Delete a specific link and trigger vector store update"""
    try:
        from services.scraped_content_manager import ScrapedContentManager
        from urllib.parse import unquote
        
        # Decode the URL parameter
        decoded_url = unquote(url)
        
        # Use ScrapedContentManager for consistent vector store updates
        manager = ScrapedContentManager()
        result = manager.remove_links([decoded_url], update_vector_store=True)
        
        if result["success"]:
            return jsonify({
                "message": f"Link deleted successfully",
                "deleted_url": decoded_url,
                "remaining_links": result.get("remaining_urls", 0),
                "vector_store_update": {
                    "status": "scheduled" if result.get("vector_update_task_id") else "not_needed",
                    "task_id": result.get("vector_update_task_id")
                }
            }), 200
        else:
            return jsonify({
                "error": result.get("error", "Failed to delete link")
            }), 404
            
    except Exception as e:
        print(f"Error deleting scraper link: {e}")
        return jsonify({"error": "Failed to delete scraper link"}), 500


@admin_bp.route('/scrapers/links/add', methods=['POST'])
@require_admin
def add_scraper_link():
    """Add a new link and trigger vector store update"""
    try:
        from services.scraped_content_manager import ScrapedContentManager
        
        data = request.get_json()
        new_url = data.get("url", "").strip()
        
        if not new_url or not new_url.startswith("http"):
            return jsonify({"error": "Valid URL is required"}), 400
        
        # Use ScrapedContentManager for consistent vector store updates
        manager = ScrapedContentManager()
        result = manager.add_links([new_url], auto_update_vector_store=True)
        
        if result["success"]:
            return jsonify({
                "message": "Link added successfully", 
                "added_url": new_url,
                "total_links": result.get("total_urls", 0),
                "scraping": {
                    "status": "started",
                    "scraping_id": result.get("scraping_id")
                },
                "vector_store_update": {
                    "status": "will_trigger_after_scraping" if result.get("auto_update_vector_store") else "disabled"
                }
            }), 200
        else:
            return jsonify({
                "error": result.get("error", "Failed to add link")
            }), 400
        
    except Exception as e:
        print(f"Error adding scraper link: {e}")
        return jsonify({"error": "Failed to add scraper link"}), 500


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

@admin_bp.route('/scrapers/status/<scraping_id>', methods=['GET'])
@require_admin  
def get_scraping_and_vector_status(scraping_id):
    """Get comprehensive status of scraping and vector store updates"""
    try:
        from services.scraped_content_manager import ScrapedContentManager
        from scrapers.services.scraping_service import get_scraping_progress
        
        # Get scraping status
        scraping_status = get_scraping_progress(scraping_id)
        
        if scraping_status is None:
            return jsonify({
                "success": False,
                "error": "Scraping session not found"
            }), 404
        
        # Build comprehensive response
        response = {
            "success": True,
            "scraping": scraping_status
        }
        
        # If there's a vector update task, get its status too
        vector_task_id = scraping_status.get("vector_update_task_id")
        if vector_task_id:
            from services.async_vectorstore_updater import get_vectorstore_update_status
            vector_status = get_vectorstore_update_status(vector_task_id)
            if vector_status:
                response["vector_store_update"] = vector_status
            else:
                response["vector_store_update"] = {"status": "not_found"}
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Error getting comprehensive status: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to get status"
        }), 500

@admin_bp.route('/content/scraping/<scraping_id>', methods=['GET'])
@require_admin
def get_content_scraping_status(scraping_id):
    """Get status of ongoing scraping operation (legacy endpoint)"""
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
