# ai/query_enhancer.py
"""
Query Enhancer - single structured Gemini call that resolves references,
detects navigation intent, and generates a HyDE hypothetical document.

Merges what used to be two separate LLM calls (query_rewrite + hyde_generate
in rag/graph_rag.py) into one: both only need "original query + conversation
history" as input and don't depend on each other's output, so there was no
reason to pay for two round trips (C3 in SPEC.md).
"""

import json
from .llm_client import get_genai_model
from .prompt_manager import PromptManager

QUERY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["REWRITE", "NAVIGATION"],
        },
        "rewritten_query": {"type": "string"},
        "hypothetical_document": {"type": "string"},
    },
    "required": ["intent", "rewritten_query", "hypothetical_document"],
}


def _format_conversation_history(conversation_history: list) -> str:
    try:
        from services.query_processor import format_conversation_history
        return format_conversation_history(conversation_history) if conversation_history else ""
    except ImportError:
        # Handle case where services module isn't available (e.g., during testing)
        if not conversation_history:
            return ""
        formatted = []
        for entry in conversation_history:
            if entry is None:
                continue
            if isinstance(entry, dict) and 'question' in entry and 'answer' in entry:
                formatted.append(f"Q: {entry['question']}\nA: {entry['answer']}")
        return "\n".join(formatted)


def analyze_query_with_context(original_query: str, conversation_history: list = None) -> dict:
    """
    Resolve references, detect navigation intent, and generate a HyDE
    hypothetical document in a single structured Gemini call.

    Args:
        original_query: The user's original query
        conversation_history: List of previous conversation exchanges

    Returns:
        {
            "intent": "REWRITE" | "NAVIGATION",
            "rewritten_query": str,   # empty when intent == NAVIGATION
            "hypothetical_document": str,  # empty when intent == NAVIGATION
        }
        On empty/None input or failure: intent defaults to "REWRITE" so the
        pipeline falls through to normal retrieval rather than silently
        treating a bad classification as a navigation query.
    """
    if not original_query or not original_query.strip():
        return {"intent": "REWRITE", "rewritten_query": "", "hypothetical_document": ""}

    formatted_history = _format_conversation_history(conversation_history)

    history_context = ""
    if formatted_history:
        history_context = f"""

    == Conversation History ==
    The user has had the following previous conversation:
    {formatted_history}

    🔍 Context-Aware Rewriting:
    - If the user's current query contains pronouns or vague references (like "it", "this course", "that program", "them"), use the conversation history to determine what they're referring to and make the query specific.
    - If the user is asking a follow-up question about something mentioned earlier, incorporate the specific course/program codes or names from the history.
    - If the user is comparing things mentioned in history, make sure to include all relevant identifiers.

    """

    template = PromptManager.get_query_rewrite_template()
    prompt = template.format(
        history_context=history_context,
        original_query=original_query
    )

    try:
        model = get_genai_model("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": QUERY_ANALYSIS_SCHEMA,
            },
        )
        result = json.loads(response.text)

        intent = result.get("intent", "REWRITE")
        if intent not in ("REWRITE", "NAVIGATION"):
            intent = "REWRITE"

        if intent == "NAVIGATION":
            rewritten_query = ""
            hypothetical_document = ""
        else:
            # Only fall back to the original query when REWRITE produced an
            # empty string (a genuine failure case) -- NAVIGATION's empty
            # rewritten_query above is intentional, not a failure.
            rewritten_query = result.get("rewritten_query", "") or original_query
            hypothetical_document = result.get("hypothetical_document", "")

        print(f"[AI Query] Intent: {intent}, Rewritten: {rewritten_query}")

        return {
            "intent": intent,
            "rewritten_query": rewritten_query,
            "hypothetical_document": hypothetical_document,
        }

    except Exception as e:
        print(f"[AI Query] Analysis error: {e}")
        return {"intent": "REWRITE", "rewritten_query": original_query, "hypothetical_document": ""}
