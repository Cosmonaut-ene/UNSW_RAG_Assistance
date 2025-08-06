from services.log_store import load_all_chat_logs
from datetime import datetime
from dateutil import tz

sydney_tz = tz.gettz('Australia/Sydney')

def export_chat_logs():
    logs = load_all_chat_logs()
    answered_count = len([log for log in logs if log.get("answered", log.get("ai_answered", False))])
    return {
        "export_time": datetime.now(sydney_tz).isoformat(),  
        "total_logs": len(logs),
        "answered": answered_count,
        "unanswered": len(logs) - answered_count,
        "logs": logs
    }