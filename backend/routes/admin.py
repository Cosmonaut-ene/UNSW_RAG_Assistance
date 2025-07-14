# routes/admin.py
import os
from flask import Blueprint, request, jsonify, make_response
from flask_cors import cross_origin
from datetime import datetime
from services.auth import require_admin, create_admin_token, verify_admin_credentials
from services.log_store import load_all_chat_logs
from services.export_chatlog import export_chat_logs
from werkzeug.utils import secure_filename
from services.log_store import load_all_chat_logs, update_chat_log_with_admin_response, delete_chat_log_by_id
admin_bp = Blueprint("admin_bp", __name__, url_prefix="/api/admin")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_FOLDER = os.path.abspath(os.path.join(CURRENT_DIR, "..", "rag", "docs"))


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

    file_path = os.path.join(DOCS_FOLDER, filename)
    file.save(file_path)
    print(f"[UPLOAD] Saved file to: {file_path}")
    return jsonify({"message": "File uploaded successfully"}), 200

@admin_bp.route('/files', methods=['GET'])
def list_files():
    files = []
    for filename in os.listdir(DOCS_FOLDER):
        if filename.endswith(".pdf"):
            files.append({
                "name": filename,
                "url": f"/docs/{filename}"
            })
    return jsonify(files)

@admin_bp.route('/delete/<path:filename>', methods=['DELETE'])
@require_admin
def delete_file(filename):
    file_path = os.path.join(DOCS_FOLDER, filename)
    print("Trying to delete:", file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": f"{filename} deleted"}), 200
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
    unanswered = [log for log in logs if not log.get("ai_answered")]
    unanswered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return jsonify({
        "total": len(unanswered),
        "unanswered": unanswered
    }), 200

@admin_bp.route('/history/<session_id>', methods=['GET'])
@require_admin
def get_session_history(session_id):
    logs = load_all_chat_logs()
    history = [log for log in logs if log.get("session_id") == session_id]
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
    total = len(logs)
    answered = len([log for log in logs if log.get("ai_answered")])
    unanswered = total - answered

    # Daily breakdown
    day_counts = {}
    for log in logs:
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
        filtered_logs = []
        
        if query_type == 'unanswered':
            filtered_logs = [log for log in all_logs if not log.get("ai_answered")]
        elif query_type == 'negative':
            filtered_logs = [log for log in all_logs if log.get("user_feedback") == "negative"]
        else:  # all
            filtered_logs = [
                log for log in all_logs 
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
                "needs_attention_reason": []
            }
            
            if not log.get("ai_answered"):
                query_item["needs_attention_reason"].append("unanswered")
            if log.get("user_feedback") == "negative":
                query_item["needs_attention_reason"].append("negative_feedback")
            
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
    

# ========== Error handlers ==========
@admin_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Admin endpoint not found'}), 404

@admin_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
