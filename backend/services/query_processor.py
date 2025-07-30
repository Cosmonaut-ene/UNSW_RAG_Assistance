# services/query_processor.py

from datetime import datetime
from difflib import SequenceMatcher
from services.log_store import load_all_chat_logs, append_chat_log
# Import modules without circular dependencies
from rag import process_with_rag_detailed, ask_with_hybrid_search  
from ai import process_query as ai_process_query
from dateutil import tz
import time
import uuid

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def estimate_tokens(text):
    if not text:
        return 0
    return len(text) // 4  #约4个字符=1个token

def get_recent_conversation_history(session_id, limit=5):
    """获取指定session的最近5轮对话历史"""
    if not session_id or session_id == "unknown_session":
        return []
    
    all_logs = load_all_chat_logs()
    # 只获取该session且AI已回答的记录，排除统计记录
    session_logs = [
        log for log in all_logs 
        if log.get('session_id') == session_id 
        and log.get('ai_answered', False)
        and log.get('question', '').strip()
        and log.get('answer', '').strip()
        and log.get("type") != "stats_summary"
    ]
    
    # 按时间倒序排列，获取最近的记录
    session_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    recent_logs = session_logs[:limit]
    
    # 转回时间顺序（旧到新）以符合对话流程
    recent_logs.reverse()
    
    print(f"[QueryProcessor] Found {len(recent_logs)} recent conversations for session {session_id}")
    return recent_logs

def format_conversation_history(history_logs):
    """将历史对话格式化为prompt可用的格式"""
    if not history_logs:
        return ""
    
    formatted_lines = []
    for i, log in enumerate(history_logs, 1):
        question = log.get('question', '').strip()
        answer = log.get('answer', '').strip()
        
        if question and answer:
            # 截断过长的答案以节省token
            if len(answer) > 200:
                answer = answer[:200] + "..."
            
            formatted_lines.append(f"用户: {question}")
            formatted_lines.append(f"助手: {answer}")
            formatted_lines.append("")  # 空行分隔
    
    return "\n".join(formatted_lines).strip()

def find_best_answer(question):
    all_logs = load_all_chat_logs()
    answered_logs = [log for log in all_logs if log.get("ai_answered") and log.get("type") != "stats_summary"] # 排除统计记录，只检查真实的查询记录
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

def process_with_ai(question, session_id=None):
    # 开始性能跟踪
    start_time = time.time()
    processing_steps = []
    cache_hit = False
    
    # 检查缓存记录
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

    question_lower = question.lower().strip()
    
    # 获取对话历史
    processing_steps.append("history_retrieval")
    conversation_history = get_recent_conversation_history(session_id) if session_id else []
    
    try:
        print("[QueryProcessor] Starting RAG workflow...")
        formatted_history = format_conversation_history(conversation_history)
        
        # Step 1: Query rewriting
        processing_steps.append("query_rewriting")
        from ai.query_processor import rewrite_query_with_context
        rewritten_query = rewrite_query_with_context(question, conversation_history)
        print(f"[QueryProcessor] Original query: {question}")
        print(f"[QueryProcessor] Rewritten query: {rewritten_query}")
        
        # Step 2: RAG search using rewritten query
        processing_steps.append("rag_search")
        rag_result = process_with_rag_detailed(rewritten_query, conversation_history=conversation_history)
        rag_search_results = rag_result.get("search_results", [])
        
        # Step 3: Hybrid search (RAG + BM25 search combination)
        processing_steps.append("hybrid_search")
        from rag.hybrid_search import HybridSearchEngine
        
        # Get vector store for BM25 indexing
        try:
            from rag import load_vector_store
            vector_store = load_vector_store()
        except Exception as e:
            print(f"[QueryProcessor] Warning: Could not load vector store for BM25: {e}")
            vector_store = None
        
        # Initialize hybrid search engine with vector store
        hybrid_engine = HybridSearchEngine(
            vector_store=vector_store,
            min_hybrid_score=40.0,  # Lower threshold for better recall
            min_bm25_score=3.0,     # BM25 minimum score
            min_rag_score=25.0      # RAG minimum score
        )
        
        # Convert RAG results to hybrid search format
        hybrid_rag_results = []
        for doc in rag_search_results:
            hybrid_rag_results.append({
                'page_content': doc.get('page_content', ''),
                'metadata': doc.get('metadata', {})
            })
        
        # Perform hybrid search
        hybrid_results = hybrid_engine.search_hybrid(rewritten_query, hybrid_rag_results, max_results=10)
        print(f"[QueryProcessor] Hybrid search returned {len(hybrid_results)} results")
        
        # Convert hybrid results back to standard format
        search_results = []
        matched_files = []
        for result in hybrid_results:
            search_results.append({
                'page_content': result.get('page_content', result.get('content', '')),
                'metadata': result.get('metadata', {})
            })
            
            # Extract file info
            metadata = result.get('metadata', {})
            source_file = metadata.get('source', 'Unknown')
            if source_file != 'Unknown':
                filename = source_file.split('/')[-1] if '/' in source_file else source_file
                if filename not in matched_files:
                    matched_files.append(filename)
        
        # Check if we have any search results, if not, use fallback immediately
        if not search_results:
            processing_steps.append("no_search_results_fallback")
            print(f"[QueryProcessor] No search results found, using direct LLM fallback")
            
            from ai.response_generator import generate_fallback_response
            fallback_answer = generate_fallback_response(rewritten_query, formatted_history)
            
            response_time = int((time.time() - start_time) * 1000)
            tokens_used = estimate_tokens(question + fallback_answer)
            return fallback_answer, True, [], {
                "response_time_ms": response_time,
                "tokens_used": tokens_used,
                "processing_steps": processing_steps,
                "cache_hit": cache_hit,
                "fallback_used": True,
                "fallback_reason": "no_search_results"
            }
        
        # Step 4: Process with AI module using hybrid search results
        processing_steps.append("ai_generation")
        ai_result = ai_process_query(rewritten_query, search_results, formatted_history)
        rag_answer = ai_result.get("answer", "")
        safety_blocked = ai_result.get("safety_blocked", False)
        
        # Update matched files if AI found more
        ai_matched_files = ai_result.get("matched_files", [])
        for file in ai_matched_files:
            if file not in matched_files:
                matched_files.append(file)
        
        # Handle safety blocked queries
        if safety_blocked:
            processing_steps.append("safety_blocked")
            print(f"[QueryProcessor] Query blocked by safety filter")
            response_time = int((time.time() - start_time) * 1000)
            tokens_used = estimate_tokens(question + rag_answer)
            return rag_answer, True, matched_files, {
                "response_time_ms": response_time,
                "tokens_used": tokens_used,
                "processing_steps": processing_steps,
                "cache_hit": cache_hit,
                "safety_blocked": True
            }
        
        if (not rag_answer) or ("i don't have any information" in rag_answer.lower()) or ("i don't know" in rag_answer.lower()) or not search_results:
            processing_steps.append("rag_fallback")
            print(f"[QueryProcessor] RAG fallback triggered: no meaningful answer, using direct LLM")
            
            # Execute fallback to direct LLM
            from ai.response_generator import generate_fallback_response
            fallback_answer = generate_fallback_response(rewritten_query, formatted_history)
            
            response_time = int((time.time() - start_time) * 1000)
            tokens_used = estimate_tokens(question + fallback_answer)
            return fallback_answer, True, [], {
                "response_time_ms": response_time,
                "tokens_used": tokens_used,
                "processing_steps": processing_steps,
                "cache_hit": cache_hit,
                "fallback_used": True
            }
        else:
            processing_steps.append("rag_success")
            print(f"[QueryProcessor] RAG Answer: {rag_answer[:50]}...")
            print(f"[QueryProcessor] Matched files: {matched_files}")
            print(f"[QueryProcessor] Used conversation history: {len(conversation_history)} previous exchanges")
            response_time = int((time.time() - start_time) * 1000)
            tokens_used = estimate_tokens(question + rag_answer)
            return rag_answer, True, matched_files, {
                "response_time_ms": response_time,
                "tokens_used": tokens_used,
                "processing_steps": processing_steps,
                "cache_hit": cache_hit
            }
    except Exception as e:
        processing_steps.append("rag_error")
        print(f"[QueryProcessor] RAG failed: {e}")

    processing_steps.append("no_answer")
    print(f"[QueryProcessor] No answer found for: {question}")
    response_time = int((time.time() - start_time) * 1000)
    tokens_used = estimate_tokens(question + "I do not know the answer to this question.")
    return "I do not know the answer to this question.", False, [], {
        "response_time_ms": response_time,
        "tokens_used": tokens_used,
        "processing_steps": processing_steps,
        "cache_hit": cache_hit
    }

def log_current_stats():
    """将记录写入chat_logs.jsonl"""
    try:
        sydney_tz = tz.gettz('Australia/Sydney')
        logs = load_all_chat_logs()
        
        # 只统计真实的查询记录（排除统计记录本身）
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
    Return message_id so that the front end can use it
    """
    sydney_tz = tz.gettz('Australia/Sydney')
    chat_entry = {
        "timestamp": datetime.now(sydney_tz).isoformat(),
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "status": "safety_blocked" if safety_blocked else ("answered" if answered else "unanswered"),
        "ai_answered": answered,
        "matched_files": matched_files or [],
        "safety_blocked": safety_blocked
    }
    
    if performance_data:
        chat_entry.update({
            "response_time_ms": performance_data.get("response_time_ms", 0),
            "tokens_used": performance_data.get("tokens_used", 0),
            "processing_steps": performance_data.get("processing_steps", []),
            "cache_hit": performance_data.get("cache_hit", False),
            "model_used": "gemini-pro",  # 默认模型
        })
    
    message_id = append_chat_log(chat_entry)
    print(f"[QueryProcessor] Saved to chat log. answered={answered}, matched_files={matched_files}, message_id={message_id}")
    if performance_data:
        print(f"[QueryProcessor] Performance: {performance_data.get('response_time_ms', 0)}ms, {performance_data.get('tokens_used', 0)} tokens")
    
    # 添加统计记录
    log_current_stats()
    
    return message_id
