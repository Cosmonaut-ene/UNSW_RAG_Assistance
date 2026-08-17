# rag/hallucination_checker.py
"""
Hallucination checking for generated answers (D3 in SPEC.md).

Two independent checks, not one keyword scan:
  a) validate_citations() -- deterministic, no LLM call. Every citation in
     the answer must correspond to a document actually retrieved for this
     query. A fabricated citation (a document that was never retrieved) is
     itself a form of hallucination.
  b) check_faithfulness() -- a single structured Gemini call judging
     whether every claim in the answer is supported by the retrieved
     context. This is what "hallucination check" should have meant all
     along; the old implementation only scanned the answer text for
     phrases like "I don't know", which catches the model being honestly
     uncertain, not the model confidently fabricating a wrong course code
     or prerequisite.
"""

import json
import re
from typing import Dict, List, Tuple

from config.rag_config import RAG_CONFIG

FAITHFULNESS_SCHEMA = {
    "type": "object",
    "properties": {
        "faithful": {"type": "boolean"},
        "unsupported_claims": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["faithful", "unsupported_claims"],
}


def validate_citations(answer: str, matched_files: List[str]) -> Tuple[bool, bool]:
    """
    Check that every citation in the answer corresponds to a document that
    was actually retrieved for this query.

    Args:
        answer: The generated answer text (expected to contain markdown
                links in its Sources section, per the RAG prompt template)
        matched_files: Filenames/course-codes of documents actually
                       retrieved and passed to generation for this query

    Returns:
        (citations_valid, citations_missing)
        citations_valid: False if any cited source isn't in matched_files
        citations_missing: True if matched_files is non-empty (real
                            context was used) but the answer cited nothing
    """
    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', answer)
    cited_keys = {url.rstrip('/').split('/')[-1].lower() for _, url in links}

    matched_lower = {f.lower() for f in matched_files}

    citations_valid = all(key in matched_lower for key in cited_keys) if cited_keys else True
    citations_missing = bool(matched_files) and not cited_keys

    return citations_valid, citations_missing


def check_faithfulness(answer: str, context_docs: List[Dict], content_key: str = "page_content") -> Dict:
    """
    Judge whether every factual claim in the answer is supported by the
    retrieved context, via a single structured Gemini call.

    Args:
        answer: The generated answer text
        context_docs: The documents that were passed to generation
        content_key: Key for document text content

    Returns:
        {"faithful": bool, "unsupported_claims": [str, ...]}
    """
    if not answer:
        return {"faithful": False, "unsupported_claims": ["(empty answer)"]}

    if "INSUFFICIENT_CONTEXT" in answer:
        # generate_node already said it couldn't answer (its own contract,
        # see D2) -- nothing to check for faithfulness. Still route to
        # fallback without spending an LLM call to confirm the obvious.
        return {"faithful": False, "unsupported_claims": []}

    if not context_docs:
        # An answer with no context to check it against can't be judged
        # faithful -- there's nothing for it to be faithful *to*.
        return {"faithful": False, "unsupported_claims": ["(no context available to verify against)"]}

    try:
        from ai.llm_client import get_genai_model
        model = get_genai_model("gemini-2.5-flash")

        context_text = "\n\n".join(
            doc.get(content_key, doc.get("content", ""))[:RAG_CONFIG.faithfulness_context_truncation]
            for doc in context_docs
        )

        prompt = (
            "You are checking whether an AI-generated answer is faithful to its source context.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Answer:\n{answer}\n\n"
            "Is every factual claim in the answer supported by the context? List any claims that "
            "are NOT supported by the context (e.g. invented course codes, prerequisites, or other "
            "details not present in the context above)."
        )

        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": FAITHFULNESS_SCHEMA,
            },
        )
        result = json.loads(response.text)

        return {
            "faithful": result.get("faithful", True),
            "unsupported_claims": result.get("unsupported_claims", []),
        }

    except Exception as e:
        print(f"[HallucinationCheck] Faithfulness check error: {e}. Defaulting to faithful (fail open).")
        return {"faithful": True, "unsupported_claims": []}
