from flask import Blueprint, request, jsonify

user_bp = Blueprint('user_bp', __name__)

# Log file
LOG_DIR = os.path.join(os.path.dirname(__file__), "log")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "chat_logs.jsonl")

@user_bp.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    question = data.get("question")
    session_id = data.get("session_id", "unknown_session")
    
    if not question:
        return jsonify({"error": "Question required"}), 400
    
    # TODO: replace with LLM call
    answer = f"You asked: {question}"

    # Log the query
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "question": question,
        "answer": answer
    }

    # Write to log file
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    return jsonify({
        "answer": answer,
        "session_id": session_id
    })


