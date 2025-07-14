# services/query_processor.py

from datetime import datetime
from difflib import SequenceMatcher
from services.log_store import load_all_chat_logs, append_chat_log
from rag import process_with_rag, process_with_rag_detailed
from dateutil import tz

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_best_answer(question):
    all_logs = load_all_chat_logs()
    answered_logs = [log for log in all_logs if log.get("ai_answered")]
    print(f"[QueryProcessor] Checking {len(answered_logs)} answered logs.")
    best_match = None
    best_similarity = 0.0
    for log in answered_logs:
        log_question = log.get("question", "")
        sim_score = similarity(question, log_question)
        if sim_score > 0.9 and sim_score > best_similarity:
            best_match = log
            best_similarity = sim_score
            print(f"[QueryProcessor] Found match: {log_question[:30]}... (similarity: {sim_score:.2f})")
    if best_match:
        return best_match.get("answer", ""), True
    print(f"[QueryProcessor] No match found in answered logs.")
    return None, False

# def get_simple_response(question_lower):
#     greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
#     if any(question_lower.startswith(greet) or f" {greet} " in question_lower for greet in greetings):
#         return "Hello! Welcome to UNSW CSE Open Day! I'm here to help answer your questions."

#     thanks = ["thanks", "thank you", "thx"]
#     if any(thank in question_lower for thank in thanks):
#         return "You're welcome! Is there anything else you'd like to know?"

#     goodbyes = ["bye", "goodbye", "see you", "good night"]
#     if any(bye in question_lower for bye in goodbyes):
#         return "Goodbye! Have a great day at UNSW CSE Open Day!"

#     if "how are you" in question_lower:
#         return "I'm doing well, thank you! How can I help you with UNSW CSE Open Day information?"

#     if "who are you" in question_lower or "what are you" in question_lower:
#         return "I'm the UNSW CSE Open Day Assistant! I'm here to help answer your questions about UNSW CSE."

#     return None

def process_with_ai(question):
    
    answer, found = find_best_answer(question)
    if found:
        return answer, True, []

    question_lower = question.lower().strip()
    
    try:
        print("[QueryProcessor] Trying RAG...")
        rag_result = process_with_rag_detailed(question)
        rag_answer = rag_result.get("answer", "")
        matched_files = rag_result.get("matched_files", [])
        
        if (not rag_answer) or ("i don't have any information" in rag_answer.lower()) or ("i don't know" in rag_answer.lower()):
            print(f"[QueryProcessor] RAG fallback triggered: no meaningful answer.")
        else:
            print(f"[QueryProcessor] RAG Answer: {rag_answer[:50]}...")
            print(f"[QueryProcessor] Matched files: {matched_files}")
            return rag_answer, True, matched_files
    except Exception as e:
        print(f"[QueryProcessor] RAG failed: {e}")

    print(f"[QueryProcessor] No answer found for: {question}")
    return "I do not know the answer to this question.", False, []

def save_to_admin_system(question, answer, answered, session_id, matched_files=None):
    """
    Return message_id so that the front end can use it
    """
    sydney_tz = tz.gettz('Australia/Sydney')
    chat_entry = {
        "timestamp": datetime.now(sydney_tz).isoformat(),
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "status": "answered" if answered else "unanswered",
        "ai_answered": answered,
        "matched_files": matched_files or []
    }
    
    message_id = append_chat_log(chat_entry)
    print(f"[QueryProcessor] Saved to chat log. answered={answered}, matched_files={matched_files}, message_id={message_id}")
    
    return message_id