# services/query_processor.py

from datetime import datetime
from difflib import SequenceMatcher
from services.log_store import load_all_chat_logs, append_chat_log
from services.cache_store import find_cached_answer, save_to_cache, get_question_hash
from dateutil import tz
import time
import uuid

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def estimate_tokens(text):
    if not text:
        return 0
    return len(text) // 4  # Approximately 4 characters = 1 token

def get_recent_conversation_history(session_id, limit=5):
    """Get recent conversation history for the specified session (last 5 rounds)"""
    if not session_id or session_id == "unknown_session":
        return []
    
    all_logs = load_all_chat_logs()
    # Only get records for this session where AI has answered, excluding stats records
    session_logs = [
        log for log in all_logs 
        if log.get('session_id') == session_id 
        and log.get('answered', log.get('ai_answered', False))
        and log.get('question', '').strip()
        and log.get('answer', '').strip()
        and log.get("type") != "stats_summary"
    ]
    
    # Sort by time in descending order, get recent records
    session_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    recent_logs = session_logs[:limit]
    
    # Reverse back to chronological order (old to new) to match conversation flow
    recent_logs.reverse()
    
    print(f"[QueryProcessor] Found {len(recent_logs)} recent conversations for session {session_id}")
    return recent_logs

def format_conversation_history(history_logs):
    """Format conversation history into a prompt-usable format"""
    if not history_logs:
        return ""
    
    formatted_lines = []
    for i, log in enumerate(history_logs, 1):
        # Handle malformed entries
        if not isinstance(log, dict):
            continue
        if log is None:
            continue
            
        question = log.get('question', '')
        answer = log.get('answer', '')
        
        # Handle None values
        if question is None:
            question = ''
        if answer is None:
            answer = ''
            
        question = question.strip()
        answer = answer.strip()
        
        if question and answer:
            # Truncate overly long answers to save tokens
            if len(answer) > 200:
                answer = answer[:200] + "..."
            
            formatted_lines.append(f"User: {question}")
            formatted_lines.append(f"Assistant: {answer}")
            formatted_lines.append("")  # Empty line separator
    
    return "\n".join(formatted_lines).strip()

def find_best_answer(question):
    """
    Find cached answer for a question using the new cache system
    Returns: (answer, found)
    """
    answer, found, cache_entry = find_cached_answer(question)
    
    if found:
        print(f"[QueryProcessor] Cache hit: {question[:30]}...")
        return answer, True
    else:
        print(f"[QueryProcessor] No cached answer found for: {question[:30]}...")
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

def process_with_ai(question, session_id=None):
    """
    Process user question through the LangGraph RAG pipeline.
    Cache check is handled here before invoking the graph.
    """
    # Start performance tracking
    start_time = time.time()
    processing_steps = []
    cache_hit = False

    # Check cache records (outside graph - fast path)
    processing_steps.append("cache_check")
    answer, found = find_best_answer(question)
    if found:
        cache_hit = True
        processing_steps.append("cache_hit")
        response_time = int((time.time() - start_time) * 1000)
        tokens_used = estimate_tokens(question + answer)
        return answer, True, [], {
            "response_time_ms": response_time,
            "tokens_used": tokens_used,
            "processing_steps": processing_steps,
            "cache_hit": cache_hit
        }

    # Get conversation history for the graph
    processing_steps.append("history_retrieval")
    conversation_history = get_recent_conversation_history(session_id) if session_id else []
    formatted_history = format_conversation_history(conversation_history)

    try:
        print("[QueryProcessor] Invoking LangGraph RAG pipeline...")
        from rag.graph_rag import invoke_rag_graph

        result = invoke_rag_graph(
            query=question,
            session_id=session_id or "",
            conversation_history=conversation_history,
            formatted_history=formatted_history,
        )

        answer = result.get("answer", "")
        answered = result.get("answered", False)
        matched_files = result.get("matched_files", [])
        retrieved_contexts = result.get("retrieved_contexts", [])
        perf = result.get("performance", {})

        # Merge processing steps
        graph_steps = perf.get("processing_steps", [])
        processing_steps.extend(graph_steps)

        response_time = int((time.time() - start_time) * 1000)
        tokens_used = estimate_tokens(question + (answer or ""))

        return answer, answered, matched_files, {
            "response_time_ms": response_time,
            "tokens_used": tokens_used,
            "processing_steps": processing_steps,
            "cache_hit": cache_hit,
            "fallback_used": perf.get("fallback_used", False),
            "safety_blocked": perf.get("safety_blocked", False),
            "warning_returned": perf.get("warning_returned", False),
            "retrieved_contexts": retrieved_contexts,
        }

    except Exception as e:
        processing_steps.append("graph_error")
        print(f"[QueryProcessor] LangGraph pipeline failed: {e}")
        import traceback
        traceback.print_exc()

        # Final fallback
        processing_steps.append("no_answer")
        response_time = int((time.time() - start_time) * 1000)
        tokens_used = estimate_tokens(question + "I do not know the answer to this question.")
        return "I do not know the answer to this question.", False, [], {
            "response_time_ms": response_time,
            "tokens_used": tokens_used,
            "processing_steps": processing_steps,
            "cache_hit": cache_hit
        }

def log_current_stats():
    """Write records to chat_logs.jsonl"""
    try:
        sydney_tz = tz.gettz('Australia/Sydney')
        logs = load_all_chat_logs()
        
        # Only count real query records (excluding stats records themselves)
        query_logs = [log for log in logs if log.get("type") != "stats_summary"]
        total_queries = len(query_logs)
        
        if total_queries == 0:
            return

        response_times = [log.get("response_time_ms", 0) for log in query_logs if log.get("response_time_ms")]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        total_tokens = sum(log.get("tokens_used", 0) for log in query_logs)

        stats_entry = {
            "timestamp": datetime.now(sydney_tz).isoformat(),
            "type": "stats_summary",
            "total_queries": total_queries,
            "avg_response_time": round(avg_response_time, 2),
            "total_tokens": total_tokens,
            "message_id": str(uuid.uuid4())
        }

        append_chat_log(stats_entry)

        print(f"[Stats] Total Queries: {total_queries} | Avg Response Time: {avg_response_time:.0f}ms | Total Tokens: {total_tokens}")
        
    except Exception as e:
        print(f"[Stats] Error calculating stats: {e}")

def save_to_admin_system(question, answer, answered, session_id, matched_files=None, safety_blocked=False, performance_data=None):
    """
    Save query to both chat log and cache system
    Return message_id so that the front end can use it
    """
    sydney_tz = tz.gettz('Australia/Sydney')
    # Determine query type based on response method
    if not answered:
        query_type = "unanswered"
    elif safety_blocked or (performance_data and (performance_data.get("safety_blocked") or performance_data.get("warning_returned"))):
        query_type = "unanswered"
    elif (performance_data and 
          (performance_data.get("fallback_used") or 
           performance_data.get("navigation_fallback"))):
        query_type = "ai_answered"
    else:
        query_type = "rag_answered"
    
    # Generate question hash for cache linking
    question_hash = get_question_hash(question) if question else None
    cache_hit = performance_data.get("cache_hit", False) if performance_data else False
    
    # Save to cache if it's a new answered query (not a cache hit)
    if answered and not cache_hit and not safety_blocked and question and answer:
        print(f"[QueryProcessor] Saving new answer to cache...")
        save_to_cache(
            question=question,
            answer=answer,
            answer_quality=query_type,
            matched_files=matched_files or []
        )
    
    chat_entry = {
        "timestamp": datetime.now(sydney_tz).isoformat(),
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "status": "safety_blocked" if safety_blocked else ("answered" if answered else "unanswered"),
        "answered": answered,
        "query_type": query_type,
        "matched_files": matched_files or [],
        "safety_blocked": safety_blocked,
        "cache_hit": cache_hit,
        "question_hash": question_hash
    }
    
    if performance_data:
        chat_entry.update({
            "response_time_ms": performance_data.get("response_time_ms", 0),
            "tokens_used": performance_data.get("tokens_used", 0),
            "processing_steps": performance_data.get("processing_steps", []),
            "model_used": "gemini-pro",  # Default model
        })
    
    message_id = append_chat_log(chat_entry)
    print(f"[QueryProcessor] Saved to chat log. answered={answered}, cache_hit={cache_hit}, matched_files={matched_files}, message_id={message_id}")
    if performance_data:
        print(f"[QueryProcessor] Performance: {performance_data.get('response_time_ms', 0)}ms, {performance_data.get('tokens_used', 0)} tokens")
    
    # Add statistics record
    log_current_stats()
    
    return message_id
