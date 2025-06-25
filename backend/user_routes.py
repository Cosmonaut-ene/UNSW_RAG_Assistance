from flask import Blueprint, request, jsonify

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    question = data.get("question")
    session_id = data.get("session_id", "unknown_session")
    
    if not question:
        return jsonify({"error": "Question required"}), 400
    
    # TODO: replace with LLM call
    return jsonify({
        "answer": f"You asked: {question}",
        "session_id": session_id
    })
