# services/cache_store.py
import os
import json
import hashlib
import uuid
from datetime import datetime
from dateutil import tz
from difflib import SequenceMatcher

# Import centralized path configuration
from config.paths import PathConfig

# Ensure directories exist
PathConfig.ensure_directories()

# Cache file
CACHE_FILE = str(PathConfig.LOGS_DIR / "query_cache.jsonl")

def normalize_question(question):
    """Normalize question text for consistent hashing"""
    return question.lower().strip()

def get_question_hash(question):
    """Generate SHA256 hash for normalized question"""
    normalized = normalize_question(question)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]

def similarity(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def load_all_cache_entries():
    """Load all cache entries from query_cache.jsonl"""
    entries = []
    if not os.path.exists(CACHE_FILE):
        print("[CacheStore] No query_cache.jsonl found, returning empty list.")
        return entries
    try:
        with open(CACHE_FILE, "r", encoding='utf-8') as f:
            for line in f:
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        print(f"[CacheStore] Loaded {len(entries)} cache entries.")
    except Exception as e:
        print(f"[CacheStore] Failed to load cache entries: {e}")
    return entries

def save_all_cache_entries(entries):
    """Save all cache entries to query_cache.jsonl"""
    try:
        with open(CACHE_FILE, "w", encoding='utf-8') as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"[CacheStore] Saved {len(entries)} cache entries.")
        return True
    except Exception as e:
        print(f"[CacheStore] Failed to save cache entries: {e}")
        return False

def find_cached_answer(question):
    """
    Find cached answer for a question
    Returns: (answer, found, cache_entry)
    """
    try:
        entries = load_all_cache_entries()
        if not entries:
            return None, False, None
        
        question_hash = get_question_hash(question)
        
        # First try exact hash match
        for entry in entries:
            if entry.get("question_hash") == question_hash:
                print(f"[CacheStore] Exact hash match found for: {question[:30]}...")
                # Increment usage count
                entry["usage_count"] = entry.get("usage_count", 0) + 1
                entry["last_used"] = datetime.now(tz.gettz('Australia/Sydney')).isoformat()
                
                # Save updated entry back
                save_all_cache_entries(entries)
                
                return entry.get("answer"), True, entry
        
        # If no exact hash match, try similarity matching
        best_match = None
        best_similarity = 0.0
        
        for entry in entries:
            cached_question = entry.get("question", "")
            sim_score = similarity(question, cached_question)
            
            # Use high similarity threshold (0.95) to ensure quality matches
            if sim_score > 0.95 and sim_score > best_similarity:
                best_match = entry
                best_similarity = sim_score
        
        if best_match:
            print(f"[CacheStore] Similarity match found: {best_match.get('question', '')[:30]}... (similarity: {best_similarity:.2f})")
            # Increment usage count
            best_match["usage_count"] = best_match.get("usage_count", 0) + 1
            best_match["last_used"] = datetime.now(tz.gettz('Australia/Sydney')).isoformat()
            
            # Save updated entry back
            save_all_cache_entries(entries)
            
            return best_match.get("answer"), True, best_match
        
        print(f"[CacheStore] No cached answer found for: {question[:30]}...")
        return None, False, None
        
    except Exception as e:
        print(f"[CacheStore] Error finding cached answer: {e}")
        return None, False, None

def save_to_cache(question, answer, answer_quality="rag_answered", matched_files=None, user_feedback=None, query_type=None):
    """
    Save or update a question-answer pair in cache
    answer_quality: "admin_answered" | "rag_answered" | "ai_answered"
    user_feedback: "positive" | "negative" | "copy" | None
    query_type: "rag_answered" | "ai_answered" | "unanswered" | None
    """
    try:
        entries = load_all_cache_entries()
        question_hash = get_question_hash(question)
        sydney_tz = tz.gettz('Australia/Sydney')
        current_time = datetime.now(sydney_tz).isoformat()
        
        # Check if entry already exists
        existing_entry = None
        for entry in entries:
            if entry.get("question_hash") == question_hash:
                existing_entry = entry
                break
        
        if existing_entry:
            # Update existing entry
            existing_entry["answer"] = answer
            existing_entry["updated_at"] = current_time
            existing_entry["answer_quality"] = answer_quality
            if matched_files is not None:
                existing_entry["matched_files"] = matched_files
            if user_feedback is not None:
                existing_entry["user_feedback"] = user_feedback
            if query_type is not None:
                existing_entry["query_type"] = query_type
            print(f"[CacheStore] Updated existing cache entry: {question[:30]}...")
        else:
            # Create new entry
            new_entry = {
                "question_hash": question_hash,
                "question": question,
                "answer": answer,
                "created_at": current_time,
                "updated_at": current_time,
                "answer_quality": answer_quality,
                "usage_count": 1,  # Start with 1 since it's being used
                "last_used": current_time,
                "matched_files": matched_files or [],
                "user_feedback": user_feedback,
                "query_type": query_type,
                "cache_id": str(uuid.uuid4())
            }
            entries.append(new_entry)
            print(f"[CacheStore] Created new cache entry: {question[:30]}...")
        
        # Save all entries back
        return save_all_cache_entries(entries)
        
    except Exception as e:
        print(f"[CacheStore] Failed to save cache entry: {e}")
        return False

def update_cached_answer(question_hash, new_answer, answer_quality="admin_answered"):
    """
    Update cached answer by question hash
    Used when admin modifies an answer
    """
    try:
        entries = load_all_cache_entries()
        updated = False
        sydney_tz = tz.gettz('Australia/Sydney')
        
        for entry in entries:
            if entry.get("question_hash") == question_hash:
                entry["answer"] = new_answer
                entry["updated_at"] = datetime.now(sydney_tz).isoformat()
                entry["answer_quality"] = answer_quality
                updated = True
                print(f"[CacheStore] Updated cache entry with hash: {question_hash}")
                break
        
        if not updated:
            print(f"[CacheStore] Cache entry with hash {question_hash} not found")
            return False
        
        return save_all_cache_entries(entries)
        
    except Exception as e:
        print(f"[CacheStore] Failed to update cached answer: {e}")
        return False

def get_cache_stats():
    """Get cache statistics"""
    try:
        entries = load_all_cache_entries()
        if not entries:
            return {
                "total_entries": 0,
                "total_usage": 0,
                "avg_usage": 0,
                "answer_quality_breakdown": {}
            }
        
        total_usage = sum(entry.get("usage_count", 0) for entry in entries)
        avg_usage = total_usage / len(entries) if entries else 0
        
        quality_breakdown = {}
        for entry in entries:
            quality = entry.get("answer_quality", "unknown")
            quality_breakdown[quality] = quality_breakdown.get(quality, 0) + 1
        
        return {
            "total_entries": len(entries),
            "total_usage": total_usage,
            "avg_usage": round(avg_usage, 2),
            "answer_quality_breakdown": quality_breakdown
        }
        
    except Exception as e:
        print(f"[CacheStore] Failed to get cache stats: {e}")
        return {"error": str(e)}

def delete_cached_entry_by_hash(question_hash):
    """Delete cached entry by question hash"""
    try:
        entries = load_all_cache_entries()
        original_count = len(entries)
        
        entries = [entry for entry in entries if entry.get("question_hash") != question_hash]
        
        if len(entries) == original_count:
            print(f"[CacheStore] Cache entry with hash {question_hash} not found for deletion")
            return False
        
        success = save_all_cache_entries(entries)
        if success:
            print(f"[CacheStore] Deleted cache entry with hash: {question_hash}")
        return success
        
    except Exception as e:
        print(f"[CacheStore] Failed to delete cache entry: {e}")
        return False

def sync_feedback_to_cache(question_hash, user_feedback=None, query_type=None):
    """
    Sync user feedback and query type to cached entry
    Used for bidirectional sync between chat logs and cache
    """
    try:
        entries = load_all_cache_entries()
        updated = False
        sydney_tz = tz.gettz('Australia/Sydney')
        
        for entry in entries:
            if entry.get("question_hash") == question_hash:
                if user_feedback is not None:
                    entry["user_feedback"] = user_feedback
                if query_type is not None:
                    entry["query_type"] = query_type
                entry["updated_at"] = datetime.now(sydney_tz).isoformat()
                updated = True
                print(f"[CacheStore] Synced feedback/type to cache for hash: {question_hash}")
                break
        
        if not updated:
            print(f"[CacheStore] Cache entry with hash {question_hash} not found for sync")
            return False
        
        return save_all_cache_entries(entries)
        
    except Exception as e:
        print(f"[CacheStore] Failed to sync feedback to cache: {e}")
        return False

def get_cache_entries_with_pagination(page=1, limit=20, query_type=None, user_feedback=None):
    """
    Get cached entries with pagination and filtering
    Returns: (entries, total_count)
    """
    try:
        all_entries = load_all_cache_entries()
        
        # Filter by query_type
        if query_type and query_type != 'all':
            all_entries = [entry for entry in all_entries if entry.get("query_type") == query_type]
        
        # Filter by user_feedback
        if user_feedback:
            if user_feedback == 'negative_feedback':
                all_entries = [entry for entry in all_entries if entry.get("user_feedback") == "negative"]
            elif user_feedback == 'positive_feedback':
                all_entries = [entry for entry in all_entries if entry.get("user_feedback") == "positive"]
        
        # Sort by last updated/created time
        all_entries.sort(key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=True)
        
        total_count = len(all_entries)
        start = (page - 1) * limit
        end = start + limit
        page_entries = all_entries[start:end]
        
        return page_entries, total_count
        
    except Exception as e:
        print(f"[CacheStore] Failed to get paginated cache entries: {e}")
        return [], 0

def migrate_legacy_query_types():
    """
    Migrate legacy cache entries to have proper query_type field
    """
    try:
        entries = load_all_cache_entries()
        updated_count = 0
        sydney_tz = tz.gettz('Australia/Sydney')
        
        for entry in entries:
            if entry.get("query_type") is None:
                # Derive query_type from answer_quality
                answer_quality = entry.get("answer_quality", "")
                if answer_quality in ["rag_answered", "admin_answered"]:
                    entry["query_type"] = "rag_answered" if entry.get("matched_files") else "ai_answered"
                elif answer_quality == "ai_answered":
                    entry["query_type"] = "ai_answered"
                else:
                    entry["query_type"] = "unanswered"
                
                entry["updated_at"] = datetime.now(sydney_tz).isoformat()
                updated_count += 1
                print(f"[CacheStore] Migrated query_type for: {entry.get('question', '')[:30]}... -> {entry['query_type']}")
        
        if updated_count > 0:
            success = save_all_cache_entries(entries)
            if success:
                print(f"[CacheStore] Successfully migrated {updated_count} entries")
                return updated_count
        else:
            print("[CacheStore] No entries needed migration")
            return 0
        
    except Exception as e:
        print(f"[CacheStore] Failed to migrate legacy query types: {e}")
        return -1

def clear_cache():
    """Clear all cache entries"""
    try:
        with open(CACHE_FILE, "w", encoding='utf-8') as f:
            pass  # Write empty content
        print("[CacheStore] Cache cleared successfully")
        return True
    except Exception as e:
        print(f"[CacheStore] Failed to clear cache: {e}")
        return False