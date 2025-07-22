# routes/user.py 
from flask import Blueprint, request, jsonify
from datetime import datetime
from services.query_processor import process_with_ai, save_to_admin_system
from services.log_store import save_feedback  

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    question = data.get("question")
    session_id = data.get("session_id", "unknown_session")

    if not question:
        return jsonify({"error": "Question required"}), 400

    print(f"\nProcessing question: {question}")

    ai_answer, can_answer, matched_files = process_with_ai(question, session_id)

    # Check if query was safety blocked
    safety_blocked = "violate safety guidelines" in ai_answer.lower()

    if safety_blocked:
        status = "safety_blocked"
        user_answer = ai_answer
        save_to_admin_system(question, ai_answer, True, session_id, [], safety_blocked=True)
        print(f"Query blocked by safety filter: {question[:30]}...")
    elif can_answer:
        status = "answered"
        user_answer = ai_answer
        save_to_admin_system(question, ai_answer, True, session_id, matched_files)
        print(f"AI provided answer: {ai_answer[:50]}...")
        if matched_files:
            print(f"Sources: {', '.join(matched_files)}")
    else:
        status = "unanswered"
        user_answer = "Thank you for your question! Our staff will answer it soon."
        save_to_admin_system(question, None, False, session_id, [])
        print("Question marked as unanswered")

    return jsonify({
        "answer": user_answer,
        "session_id": session_id,
        "status": status
    })

# feedback
@user_bp.route('/feedback', methods=['POST'])
def submit_feedback():

    data = request.get_json()
    session_id = data.get("session_id")
    feedback_type = data.get("feedback_type")  # 'positive', 'negative', 'copy'
    timestamp_hint = data.get("timestamp")     
    question_text = data.get("question_text")  

    if not session_id or not feedback_type:
        return jsonify({"error": "session_id and feedback_type are required"}), 400

    valid_feedback_types = ['positive', 'negative', 'copy']
    if feedback_type not in valid_feedback_types:
        return jsonify({"error": f"Invalid feedback_type. Must be one of: {valid_feedback_types}"}), 400

    try:
        # Question text matching
        feedback_saved = save_feedback(session_id, feedback_type, timestamp_hint, question_text)
        
        if feedback_saved:
            print(f"Feedback saved: {feedback_type} for session {session_id}")
            if question_text:
                print(f"  Question matched: {question_text[:30]}...")
            return jsonify({
                "message": "Feedback submitted successfully",
                "feedback_type": feedback_type,
                "session_id": session_id
            }), 200
        else:
            return jsonify({"error": "Failed to save feedback or message not found"}), 404
            
    except Exception as e:
        print(f"Error saving feedback: {e}")
        return jsonify({"error": "Internal server error"}), 500