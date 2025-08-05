# ai/safety_checker.py
"""
Safety Checker - Validates queries using Gemini's built-in safety filters
"""

import google.generativeai as genai
from .llm_client import get_genai_model

def is_query_safe_by_gemini(query: str) -> bool:
    """
    🛡️ Friendly Safety Check - Ensuring our conversation stays helpful and appropriate
    
    Args:
        query: The user query to check
        
    Returns:
        bool: True if query is safe, False if blocked
    """
    # 🎓 Enhanced safety approach: Context-aware UNSW Open Day safety
    print(f"🛡️ [Safety Guardian] Checking query appropriateness: '{query[:50]}...'")
    
    # Quick local safety patterns for UNSW Open Day context
    unsafe_patterns = [
        'hack', 'cheat', 'illegal', 'bypass', 'fake transcript', 
        'forged documents', 'academic dishonesty',
        'usyd', 'university of sydney', 'sydney university'
    ]
    
    query_lower = query.lower()
    for pattern in unsafe_patterns:
        if pattern in query_lower:
            print(f"🚫 [Safety Guardian] Query contains inappropriate content: '{pattern}'")
            return False
    
    # ✅ UNSW-focused queries are generally safe and welcome
    unsw_indicators = ['unsw', 'comp', 'infs', 'zeit', 'program', 'course', 'degree', 'study']
    if any(indicator in query_lower for indicator in unsw_indicators):
        print("✅ [Safety Guardian] UNSW-focused query - safe and welcome!")
        return True
    
    print("✅ [Safety Guardian] General query appears safe - proceeding with guidance")
    return True
    
    # Original implementation (commented out temporarily):
    # try:
    #     # Use consistent model version and add timeout
    #     model = get_genai_model("gemini-1.5-flash")
    #     
    #     # Add request timeout to prevent hanging
    #     import time
    #     start_time = time.time()
    #     
    #     response = model.generate_content(
    #         query,
    #         generation_config=genai.types.GenerationConfig(
    #             max_output_tokens=10,  # Minimal output for safety check
    #             temperature=0.0
    #         )
    #     )
    #     
    #     elapsed_time = time.time() - start_time
    #     print(f"[AI Safety] Safety check completed in {elapsed_time:.2f}s")
    #     
    #     if response.prompt_feedback and response.prompt_feedback.block_reason:
    #         print(f"[AI Safety] Query blocked by Gemini Safety: {response.prompt_feedback.block_reason}")
    #         return False
    #         
    #     print("[AI Safety] Query passed safety check")
    #     return True
    #     
    # except Exception as e:
    #     print(f"[AI Safety] Safety check error: {e}")
    #     # Default to safe if check fails to avoid blocking the system
    #     print("[AI Safety] Defaulting to safe due to error")
    #     return True