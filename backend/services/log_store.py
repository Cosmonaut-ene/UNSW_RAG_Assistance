# services/log_store.py
import os
import json
import uuid
from datetime import datetime
from dateutil import tz

# Import centralized path configuration
from config.paths import PathConfig

# Ensure directories exist
PathConfig.ensure_directories()

# File
LOG_FILE = str(PathConfig.LOGS_DIR / "chat_logs.jsonl")

def append_chat_log(entry):
    """
    Append a single user interaction to chat_logs.jsonl
    entry: dict with {timestamp, session_id, question, answer, status, answered, query_type}
    Add message_id for subsequent feedback updates
    """
    try:
        if 'message_id' not in entry:
            entry['message_id'] = str(uuid.uuid4())
        
        with open(LOG_FILE, "a", encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"[AdminStore] Appended chat log. Session: {entry.get('session_id')}, Message ID: {entry.get('message_id')}")
        
        return entry['message_id']
    except Exception as e:
        print(f"[AdminStore] Failed to append to chat log: {e}")
        return None

def load_all_chat_logs():
    """
    Load all chat logs from chat_logs.jsonl
    """
    logs = []
    if not os.path.exists(LOG_FILE):
        print("[AdminStore] No chat_logs.jsonl found, returning empty list.")
        return logs
    try:
        with open(LOG_FILE, "r", encoding='utf-8') as f:
            for line in f:
                try:
                    logs.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        print(f"[AdminStore] Loaded {len(logs)} chat log entries.")
    except Exception as e:
        print(f"[AdminStore] Failed to load chat logs: {e}")
    return logs

def update_chat_log_with_feedback(message_id, feedback_type):
    """
    Update the chat record and add feedback information
    """
    sydney_tz = tz.gettz('Australia/Sydney')
    try:
        logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding='utf-8') as f:
                for line in f:
                    try:
                        logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        
        # Find the corresponding record and update it
        updated = False
        for log in logs:
            if log.get('message_id') == message_id:
                # Add a feedback field in the chat record
                log['user_feedback'] = feedback_type
                log['feedback_time'] = datetime.now(sydney_tz).isoformat()
                updated = True
                print(f"[AdminStore] Updated chat log {message_id} with feedback: {feedback_type}")
                break
        
        if not updated:
            print(f"[AdminStore] Message {message_id} not found for feedback update")
            return False
        
        with open(LOG_FILE, "w", encoding='utf-8') as f:
            for log in logs:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")
        
        return True
        
    except Exception as e:
        print(f"[AdminStore] Failed to update feedback: {e}")
        return False

def get_message_id_by_session_and_time_and_question(session_id, timestamp_hint=None, question_text=None):
    """
    Find the most accurate message_id through session_id, time and question text
    """
    try:
        logs = load_all_chat_logs()
        session_logs = [log for log in logs if log.get('session_id') == session_id]
        
        if not session_logs:
            print(f"[AdminStore] No logs found for session: {session_id}")
            return None
        
        # Give priority to matching through question text
        if question_text:
            for log in session_logs:
                if log.get('question', '').strip().lower() == question_text.strip().lower():
                    print(f"[AdminStore] Found exact question match: {question_text}")
                    return log.get('message_id')
            
            # Try partial matching
            for log in session_logs:
                if question_text.strip().lower() in log.get('question', '').strip().lower():
                    print(f"[AdminStore] Found partial question match: {question_text}")
                    return log.get('message_id')
        
        # Sort by time
        session_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        if timestamp_hint:
            try:
                hint_time = datetime.fromisoformat(timestamp_hint.replace('Z', '+00:00'))
                closest_log = min(session_logs, key=lambda x: abs(
                    datetime.fromisoformat(x.get("timestamp", "").replace('Z', '+00:00')) - hint_time
                ))
                print(f"[AdminStore] Found closest time match for: {timestamp_hint}")
                return closest_log.get('message_id')
            except Exception as e:
                print(f"[AdminStore] Time parsing failed: {e}")
                pass
        
        print(f"[AdminStore] Using latest message for session: {session_id}")
        return session_logs[0].get('message_id')
        
    except Exception as e:
        print(f"[AdminStore] Failed to get message_id: {e}")
        return None

def save_feedback(session_id, feedback_type, timestamp_hint=None, question_text=None):
    """
    改进版反馈保存：使用多种方式定位消息
    """
    message_id = get_message_id_by_session_and_time_and_question(
        session_id, timestamp_hint, question_text
    )
    
    if not message_id:
        print(f"[AdminStore] Could not find message to update feedback for session: {session_id}")
        return False
    
    return update_chat_log_with_feedback(message_id, feedback_type)

# def get_feedback_stats():
#     """
#     从聊天记录中统计反馈数据
#     """
#     logs = load_all_chat_logs()
#     stats = {
#         'total_feedback': 0,
#         'positive': 0,
#         'negative': 0,
#         'copy': 0
#     }
    
#     for log in logs:
#         feedback = log.get('user_feedback')
#         if feedback:
#             stats['total_feedback'] += 1
#             if feedback == 'positive':
#                 stats['positive'] += 1
#             elif feedback == 'negative':
#                 stats['negative'] += 1
#             elif feedback == 'copy':
#                 stats['copy'] += 1
    
#     return stats
def update_chat_log_with_admin_response(message_id, admin_response):
    """
    Update the answer
    """
    try:
        logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding='utf-8') as f:
                for line in f:
                    try:
                        logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        
        updated = False
        for log in logs:
            if log.get('message_id') == message_id:
                log['answer'] = admin_response
                log['answered'] = True  
                log['status'] = 'answered'
                log['admin_answered'] = True  
                log['admin_response_time'] = datetime.utcnow().isoformat()
                updated = True
                print(f"[AdminStore] Updated message {message_id} with admin response")
                break
        
        if not updated:
            print(f"[AdminStore] Message {message_id} not found for admin response")
            return False
        
        with open(LOG_FILE, "w", encoding='utf-8') as f:
            for log in logs:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")
        
        return True
        
    except Exception as e:
        print(f"[AdminStore] Failed to update admin response: {e}")
        return False

def delete_chat_log_by_id(message_id):

    try:
        logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding='utf-8') as f:
                for line in f:
                    try:
                        logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        
        original_count = len(logs)
        logs = [log for log in logs if log.get('message_id') != message_id]
        
        if len(logs) == original_count:
            print(f"[AdminStore] Message {message_id} not found for deletion")
            return False
        
        with open(LOG_FILE, "w", encoding='utf-8') as f:
            for log in logs:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")
        
        print(f"[AdminStore] Deleted message {message_id}")
        return True
        
    except Exception as e:
        print(f"[AdminStore] Failed to delete message: {e}")
        return False
