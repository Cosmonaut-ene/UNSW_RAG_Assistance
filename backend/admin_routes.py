from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
import jwt
import datetime
import json
import os
import uuid
from functools import wraps

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/api/admin')

ADMIN_EMAIL = "admin@unsw.edu.au"
ADMIN_PASSWORD = "unswcse2025"

# File path configuration
DATA_DIR = "data"
QUERIES_FILE = os.path.join(DATA_DIR, "queries.json")

def ensure_data_directory():
    """Make sure the data directory exists"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created data directory: {DATA_DIR}")

def load_queries():
    """Load the question-and-answer record from the file"""
    ensure_data_directory()
    if not os.path.exists(QUERIES_FILE):
        return []
    
    try:
        with open(QUERIES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"✅ Loaded {len(data)} queries from file")
            return data
    except Exception as e:
        print(f"❌ Error loading queries: {e}")
        return []

def save_queries(queries):
    """Save the question-and-answer records to a file"""
    ensure_data_directory()
    try:
        with open(QUERIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(queries, f, ensure_ascii=False, indent=2, default=str)
        print(f"✅ Saved {len(queries)} queries to file")
        return True
    except Exception as e:
        print(f"❌ Error saving queries: {e}")
        return False

def add_query(question, answer=None, answered=False, session_id=None, ip_address=None):
    """Add a new question-and-answer record"""
    queries = load_queries()
    
    new_query = {
        "id": str(uuid.uuid4()),
        "question": question,
        "answer": answer,
        "answered": answered,
        "timestamp": datetime.datetime.now().isoformat(),
        "session_id": session_id,
        "ip_address": ip_address,
        "answered_at": None,
        "answered_by": None
    }
    
    queries.append(new_query)
    save_queries(queries)
    return new_query["id"]

def update_query(query_id, answer, answered_by="admin"):
    """Update the question-and-answer record"""
    queries = load_queries()
    
    for query in queries:
        if query["id"] == query_id:
            query["answer"] = answer
            query["answered"] = True
            query["answered_at"] = datetime.datetime.now().isoformat()
            query["answered_by"] = answered_by
            success = save_queries(queries)
            if success:
                print(f"✅ Updated query {query_id}")
            return success
    
    print(f"❌ Query {query_id} not found")
    return False

def delete_query_by_id(query_id):
    """Delete the question-and-answer record"""
    queries = load_queries()
    
    for i, query in enumerate(queries):
        if query["id"] == query_id:
            del queries[i]
            success = save_queries(queries)
            if success:
                print(f"✅ Deleted query {query_id}")
            return success
    
    print(f"❌ Query {query_id} not found for deletion")
    return False

# JWT Authentication
def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Missing token"}), 401
        try:
            token = token.split(" ")[1]
            decoded = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            if decoded.get("role") != "admin":
                return jsonify({"error": "Admin access required"}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401
        return f(*args, **kwargs)
    return wrapper

# Admin Login
@admin_bp.route('/login', methods=['POST'])
@cross_origin()
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        token = jwt.encode(
            {
                "role": "admin",
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            },
            current_app.config["SECRET_KEY"],
            algorithm="HS256"
        )
        return jsonify({
            "token": token,
            "message": "Login successful",
            "expires_in": "1 hour"
        }), 200
    
    return jsonify({"error": "Invalid credentials"}), 401

@admin_bp.route('/verify-token', methods=['GET'])
@require_admin
def verify_token():
    """tokenVerify whether the token is valid"""
    return jsonify({
        "valid": True,
        "message": "Token is valid",
        "role": "admin"
    }), 200

@admin_bp.route('/unanswered-queries', methods=['GET'])
@require_admin
def get_unanswered_queries():
    """Get the unanswered questions"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        # Load data from the file
        all_queries = load_queries()
        
        # Filter the unanswered questions
        unanswered = [q for q in all_queries if not q["answered"]]
        
        # Sort in reverse chronological order
        unanswered.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Pagination processing
        total = len(unanswered)
        start = (page - 1) * limit
        end = start + limit
        page_queries = unanswered[start:end]
        
        return jsonify({
            "queries": page_queries,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 0
        }), 200
        
    except Exception as e:
        print(f"Error fetching unanswered queries: {str(e)}")
        return jsonify({"error": "Failed to fetch queries"}), 500

@admin_bp.route('/answered-queries', methods=['GET'])
@require_admin
def get_answered_queries():
    """Get the answered questions"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        # Load data from the file
        all_queries = load_queries()
        
        # Filter the answered questions
        answered = [q for q in all_queries if q["answered"]]
        
        # Sort in reverse chronological order
        answered.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Pagination processing
        total = len(answered)
        start = (page - 1) * limit
        end = start + limit
        page_queries = answered[start:end]
        
        return jsonify({
            "queries": page_queries,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 0
        }), 200
        
    except Exception as e:
        print(f"Error fetching answered queries: {str(e)}")
        return jsonify({"error": "Failed to fetch queries"}), 500

@admin_bp.route('/add-response', methods=['POST'])
@require_admin
def add_response():
    """Add answers to the unanswered questions"""
    try:
        data = request.get_json()
        query_id = data.get("id")
        response_text = data.get("response")

        if not query_id or not response_text:
            return jsonify({"error": "Missing query ID or response"}), 400

        print(f"🔄 Adding response to query {query_id}")

        # update the query with the response
        success = update_query(query_id, response_text, "admin")
        
        if not success:
            return jsonify({"error": "Query not found"}), 404

        # get the question text from the queries file
        queries = load_queries()
        question = None
        for q in queries:
            if q["id"] == query_id:
                question = q["question"]
                break

        # upload the response to the knowledge base
        try:
            # check if the functions are available
            from app import append_to_pdf, update_vectorstore
            
            if question:
                pdf_success = append_to_pdf(question, response_text)
                if pdf_success:
                    print(f"Added Q&A to PDF: {question[:50]}...")
                    update_vectorstore(question, response_text)
                    print("Vector store updated successfully")
        except ImportError:
            print("Knowledge base update functions not available (this is OK for demo)")
        except Exception as e:
            print(f"Error updating knowledge base: {str(e)}")

        print(f"✅ Response added for question: {question[:50] if question else 'Unknown'}...")
        print(f"Answer: {response_text[:50]}...")

        return jsonify({
            "message": "Response added successfully",
            "query_id": query_id
        }), 200
        
    except Exception as e:
        print(f"❌ Error adding response: {str(e)}")
        return jsonify({"error": "Failed to add response"}), 500

@admin_bp.route('/update-answer', methods=['POST'])
@require_admin
def update_answer():
    """upload the answer to the question"""
    try:
        data = request.get_json()
        query_id = data.get("id")
        new_answer = data.get("answer")

        if not query_id or not new_answer:
            return jsonify({"error": "Missing query ID or answer"}), 400

        print(f"🔄 Updating answer for query {query_id}")
        print(f"New answer: {new_answer[:100]}...")

        # upload the queries from the file
        queries = load_queries()
        
        # find the query to update
        query_found = False
        question = None
        old_answer = None
        
        for query in queries:
            if query["id"] == query_id:
                # save the old answer and question for logging
                old_answer = query.get("answer", "No previous answer")
                question = query["question"]
                
                # update the query
                query["answer"] = new_answer
                query["answered"] = True
                query["answered_at"] = datetime.datetime.now().isoformat()
                query["answered_by"] = "admin"
                query_found = True
                
                print(f"📝 Found query to update:")
                print(f"   Question: {question[:50]}...")
                print(f"   Old answer: {old_answer[:50]}...")
                print(f"   New answer: {new_answer[:50]}...")
                break
        
        if not query_found:
            print(f"❌ Query {query_id} not found")
            return jsonify({"error": "Query not found"}), 404

        # save the updated queries
        print(f"💾 Saving updated data...")
        success = save_queries(queries)
        
        if not success:
            print(f"❌ Failed to save updated data")
            return jsonify({"error": "Failed to save updated answer"}), 500

        # verify the update
        print(f"🔍 Verifying save...")
        verification_queries = load_queries()
        verification_success = False
        for q in verification_queries:
            if q["id"] == query_id and q["answer"] == new_answer:
                verification_success = True
                print(f"✅ Verification successful: Answer updated in file")
                break
        
        if not verification_success:
            print(f"❌ Verification failed: Answer not updated in file")

        # update knowledge base 
        try:
            from app import append_to_pdf, update_vectorstore
            
            if question:
                pdf_success = append_to_pdf(question, new_answer)
                if pdf_success:
                    print(f"Updated Q&A in PDF: {question[:50]}...")
                    update_vectorstore(question, new_answer)
                    print("Vector store updated successfully")
        except ImportError:
            print("Knowledge base update functions not available")
        except Exception as e:
            print(f"Error updating knowledge base: {str(e)}")

        print(f"✅ Answer update completed for question: {question[:50] if question else 'Unknown'}...")

        return jsonify({
            "message": "Answer updated successfully",
            "query_id": query_id,
            "verification": verification_success
        }), 200
        
    except Exception as e:
        print(f"❌ Error updating answer: {str(e)}")
        return jsonify({"error": "Failed to update answer"}), 500

@admin_bp.route('/delete-query/<query_id>', methods=['DELETE'])
@require_admin
def delete_query(query_id):
    """Delete the problem"""
    try:
        success = delete_query_by_id(query_id)
        
        if success:
            return jsonify({"message": "Query deleted successfully"}), 200
        else:
            return jsonify({"error": "Query not found"}), 404
        
    except Exception as e:
        print(f"Error deleting query: {str(e)}")
        return jsonify({"error": "Failed to delete query"}), 500

@admin_bp.route('/stats', methods=['GET'])
@require_admin
def get_admin_stats():
    """Obtain the administrator statistics"""
    try:
        queries = load_queries()
        
        total_queries = len(queries)
        answered_queries = len([q for q in queries if q["answered"]])
        unanswered_queries = total_queries - answered_queries
        
        # Today's statistics
        today = datetime.datetime.now().date().isoformat()
        today_queries = len([q for q in queries if q["timestamp"].startswith(today)])
        
        # This week's statistics
        week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).date().isoformat()
        week_queries = len([q for q in queries if q["timestamp"] >= week_ago])
        
        return jsonify({
            "total_queries": total_queries,
            "answered_queries": answered_queries,
            "unanswered_queries": unanswered_queries,
            "today_queries": today_queries,
            "week_queries": week_queries,
            "response_rate": round((answered_queries / total_queries * 100), 2) if total_queries > 0 else 0
        }), 200
        
    except Exception as e:
        print(f"Error fetching admin stats: {str(e)}")
        return jsonify({"error": "Failed to fetch statistics"}), 500

@admin_bp.route('/export-data', methods=['GET'])
@require_admin
def export_data():
    """Export all data"""
    try:
        queries = load_queries()
        
        # Calculate statistical information
        total_queries = len(queries)
        answered_queries = len([q for q in queries if q["answered"]])
        unanswered_queries = total_queries - answered_queries
        
        export_data = {
            "export_time": datetime.datetime.now().isoformat(),
            "stats": {
                "total_queries": total_queries,
                "answered_queries": answered_queries,
                "unanswered_queries": unanswered_queries,
                "response_rate": round((answered_queries / total_queries * 100), 2) if total_queries > 0 else 0
            },
            "queries": queries
        }
        
        return jsonify(export_data), 200
        
    except Exception as e:
        print(f"Error exporting data: {str(e)}")
        return jsonify({"error": "Failed to export data"}), 500

@admin_bp.route('/query-analytics', methods=['GET'])
@require_admin
def get_query_analytics():
    """Obtain query analysis data"""
    try:
        queries = load_queries()
        
        # day
        daily_counts = {}
        hourly_counts = {}
        session_counts = {}
        
        for query in queries:
            timestamp = query.get("timestamp", "")
            session_id = query.get("session_id", "unknown")
            
            if timestamp:
                # date and hour processing
                try:
                    dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    date_str = dt.date().isoformat()
                    hour = dt.hour
                    
                    daily_counts[date_str] = daily_counts.get(date_str, 0) + 1
                    hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
                except:
                    pass
            
            # session ID processing
            session_counts[session_id] = session_counts.get(session_id, 0) + 1
        
        # a list format
        daily_trends = [{"date": k, "count": v} for k, v in sorted(daily_counts.items())]
        hourly_distribution = [{"hour": k, "count": v} for k, v in sorted(hourly_counts.items())]
        
        # The most active conversation
        top_sessions = sorted(session_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_sessions = [{"session_id": k, "query_count": v} for k, v in top_sessions]
        
        return jsonify({
            "daily_trends": daily_trends,
            "hourly_distribution": hourly_distribution,
            "top_sessions": top_sessions,
            "total_sessions": len(session_counts),
            "avg_queries_per_session": round(len(queries) / len(session_counts), 2) if session_counts else 0
        }), 200
        
    except Exception as e:
        print(f"Error in analytics endpoint: {str(e)}")
        return jsonify({"error": "Failed to generate analytics"}), 500

# error handlers for the admin routes
@admin_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Admin endpoint not found'}), 404

@admin_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# The functions provided for the main application to call
def save_user_query(question, answer=None, answered=False, session_id=None, ip_address=None):
    return add_query(question, answer, answered, session_id, ip_address)
