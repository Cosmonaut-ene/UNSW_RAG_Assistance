from flask import Blueprint, request, jsonify
import os
from datetime import datetime
import json
from difflib import SequenceMatcher

user_bp = Blueprint('user_bp', __name__)

# Log file
LOG_DIR = os.path.join(os.path.dirname(__file__), "log")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "chat_logs.jsonl")

def similarity(a, b):
    """Calculate the similarity of the two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def load_answered_questions():
    """Load the answered questions from the administrator system"""
    try:
        from admin_routes import load_queries
        queries = load_queries()
        answered_queries = [q for q in queries if q.get('answered', False)]
        print(f"📚 Loaded {len(answered_queries)} answered questions")
        return answered_queries
    except Exception as e:
        print(f"⚠️ Could not load answered questions: {e}")
        return []

def find_best_answer(question):
    """Find the best matching answer"""
    answered_questions = load_answered_questions()
    
    print(f"Checking {len(answered_questions)} answered questions")
    
    # Find the problem with the highest similarity
    best_match = None
    best_similarity = 0.0
    
    for qa in answered_questions:
        qa_question = qa.get('question', '')
        similarity_score = similarity(question, qa_question)
        
        if similarity_score > 0.8 and similarity_score > best_similarity:
            best_match = qa
            best_similarity = similarity_score
            print(f"Found match: {qa_question[:30]}... (similarity: {similarity_score:.2f})")
    
    if best_match:
        return best_match.get('answer', ''), True
    
    print(f"No match found")
    return None, False


def process_with_ai(question):
    """Handle AI responses"""
    
    # 1. First, check the questions that the administrator has answered
    answer, found = find_best_answer(question)
    if found:
        return answer, True
    
    # 2. AI answer
    def get_simple_response(question_lower):
        
        # Greeting
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
        for greeting in greetings:
            if greeting in question_lower:
                return "Hello! Welcome to UNSW Open Day! I'm here to help answer your questions."
        
        # thank
        thanks = ["thanks", "thank you", "thx"]
        for thank in thanks:
            if thank in question_lower:
                return "You're welcome! Is there anything else you'd like to know?"
        
        # bye
        goodbyes = ["bye", "goodbye", "see you", "good night"]
        for goodbye in goodbyes:
            if goodbye in question_lower:
                return "Goodbye! Have a great day at UNSW Open Day!"
        
        if "how are you" in question_lower:
            return "I'm doing well, thank you! How can I help you with UNSW Open Day information?"
        
        if "who are you" in question_lower or "what are you" in question_lower:
            return "I'm the UNSW Open Day Assistant! I'm here to help answer your questions about UNSW."
        
        return None  
    
    question_lower = question.lower().strip()
    
    # Try to answer simply
    simple_answer = get_simple_response(question_lower)
    if simple_answer:
        print(f"✅ Found simple response match")
        return simple_answer, True
    
    # 3. If none of them match, return "Don't know".
    print(f"❓ No answer found for: {question}")
    return "I do not know the answer to this question.", False

def save_to_admin_system(question, answer, answered, session_id, ip_address):
    """Save to the administrator system"""
    try:
        from admin_routes import save_user_query
        save_user_query(
            question=question,
            answer=answer,
            answered=answered,
            session_id=session_id,
            ip_address=ip_address
        )
        print(f"💾 Saved to admin system: answered={answered}")
    except Exception as e:
        print(f"Failed to save to admin system: {e}")

@user_bp.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    question = data.get("question")
    session_id = data.get("session_id", "unknown_session")
    
    if not question:
        return jsonify({"error": "Question required"}), 400
    
    print(f"\n🔍 Processing question: {question}")
    
    ai_answer, can_answer = process_with_ai(question)
    
    if can_answer:
        # can answer, mark as answered
        status = "answered"
        user_answer = ai_answer
        answered = True
        
        print(f"✅ AI provided answer: {ai_answer[:50]}...")
        
        # save to admin system
        save_to_admin_system(question, ai_answer, True, session_id, request.remote_addr)
        
    else:
        # ai cannot answer, mark as unanswered
        status = "unanswered"
        user_answer = "Thank you for your question! Our staff will answer it soon."
        answered = False
        
        print(f"Question marked as unanswered")
        
        # save
        save_to_admin_system(question, None, False, session_id, request.remote_addr)

    # Log the query
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "question": question,
        "answer": user_answer,
        "status": status,
        "ai_answered": answered
    }

    with open(LOG_FILE, "a", encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    return jsonify({
        "answer": user_answer,
        "session_id": session_id,
        "status": status
    })

@user_bp.route('/health', methods=['GET'])
def health():
    """health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "user_query_service",
        "timestamp": datetime.utcnow().isoformat()
    })

@user_bp.route('/history/<session_id>', methods=['GET'])
def get_history(session_id):
    """get the query history for a session"""
    try:
        history = []
        
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("session_id") == session_id:
                            history.append({
                                "timestamp": entry["timestamp"],
                                "question": entry["question"],
                                "answer": entry["answer"],
                                "status": entry.get("status", "unknown")
                            })
                    except json.JSONDecodeError:
                        continue
        
        # Sort history by timestamp
        history.sort(key=lambda x: x["timestamp"])
        
        return jsonify({
            "session_id": session_id,
            "history": history,
            "count": len(history)
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch history: {str(e)}"}), 500
