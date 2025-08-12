# ai/query_enhancer.py
"""
Query Enhancer - Handles query enhancement, rewriting, and conversation context
"""

from .llm_client import get_genai_model
from .prompt_manager import PromptManager

def rewrite_query_with_context(original_query: str, conversation_history: list = None) -> str:
    """
    Rewrite query using Gemini with conversation history context
    
    Args:
        original_query: The user's original query
        conversation_history: List of previous conversation exchanges
        
    Returns:
        str: Enhanced/rewritten query
    """
    # Format conversation history for context
    from services.query_processor import format_conversation_history
    formatted_history = format_conversation_history(conversation_history) if conversation_history else ""
    
    history_context = ""
    if formatted_history:
        history_context = f"""
    
    == Conversation History ==
    The user has had the following previous conversation:
    {formatted_history}
    
    🔍 Context-Aware Rewriting:
    - If the user's current query contains pronouns or vague references (like "it", "this course", "that program", "them", "这个", "那个"), use the conversation history to determine what they're referring to and make the query specific.
    - If the user is asking a follow-up question about something mentioned earlier, incorporate the specific course/program codes or names from the history.
    - If the user is comparing things mentioned in history, make sure to include all relevant identifiers.
    
    """
    
    # Get query rewrite template
    template = PromptManager.get_query_rewrite_template()
    prompt = template.format(
        history_context=history_context,
        original_query=original_query
    )
    
    try:
        model = get_genai_model("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip().split("\n")[0]
    except Exception as e:
        print(f"[AI Query] Rewrite error: {e}")
        return original_query

def enhance_query(query: str, conversation_history: list = None) -> str:
    """
    Enhance query for better retrieval (alias for rewrite_query_with_context)
    """
    return rewrite_query_with_context(query, conversation_history)