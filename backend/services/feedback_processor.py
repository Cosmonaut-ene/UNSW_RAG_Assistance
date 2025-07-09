# feedback_processor.py
from services.log_store import save_feedback

def process_feedback(data):
    """
    Handles feedback data:
    - Validates fields
    - Saves feedback via save_feedback()
    - Returns dict with { body, status }
    """
    session_id = data.get("session_id")
    feedback_type = data.get("feedback_type")  # 'positive', 'negative', 'copy'
    timestamp_hint = data.get("timestamp")
    question_text = data.get("question_text")

    if not session_id or not feedback_type:
        return {
            "body": {"error": "session_id and feedback_type are required"},
            "status": 400
        }

    valid_feedback_types = ['positive', 'negative', 'copy']
    if feedback_type not in valid_feedback_types:
        return {
            "body": {"error": f"Invalid feedback_type. Must be one of: {valid_feedback_types}"},
            "status": 400
        }

    feedback_saved = save_feedback(session_id, feedback_type, timestamp_hint, question_text)

    if feedback_saved:
        print(f"[Feedback] Saved: {feedback_type} for session {session_id}")
        return {
            "body": {
                "message": "Feedback submitted successfully",
                "feedback_type": feedback_type,
                "session_id": session_id
            },
            "status": 200
        }
    else:
        return {
            "body": {"error": "Failed to save feedback or message not found"},
            "status": 404
        }
