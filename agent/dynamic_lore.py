"""
Dynamic Lore Module - agent/dynamic_lore.py

Retrieves relevant lore chunks based on user input using semantic search.
Uses the main semantic search index (shared with episodes and memory).

Usage:
    from agent.dynamic_lore import get_dynamic_lore
    
    lore_block = get_dynamic_lore("tell me about yourself", k=4)
"""

import os
import sys

# Handle imports when run as script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from agent.semantic_search import search


def get_dynamic_lore(user_input: str, k: int = 4) -> str:
    """
    Get relevant lore chunks for a user input.
    
    Uses the shared semantic search index to find the top-k most relevant
    lore chunks based on the user's query.
    
    Args:
        user_input: The user's message
        k: Number of chunks to retrieve (default 4)
        
    Returns:
        Formatted lore block as bullet list
    """
    try:
        # Search semantic index for relevant chunks
        results = search(user_input, k=k * 2)  # Get more to filter for lore
        
        # Filter to only lore sources and format
        lore_lines = []
        seen_texts = set()  # Deduplicate
        
        for source, text, score in results:
            # Only include lore chunks
            if not source.startswith("lore/"):
                continue
            
            # Deduplicate (sometimes overlapping chunks are similar)
            text_key = text[:50]  # Use first 50 chars as key
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)
            
            # Clean up text
            clean_text = ' '.join(text.split())
            if clean_text:
                lore_lines.append(f"- {clean_text}")
            
            # Stop when we have enough
            if len(lore_lines) >= k:
                break
        
        if lore_lines:
            return "\n".join(lore_lines)
        else:
            # Fallback if no lore found
            return "- AI is a helpful assistant connected to User."
            
    except Exception as e:
        print(f"[DynamicLore] Error retrieving lore: {e}")
        # Fallback content
        return "- AI is a helpful assistant connected to User."


# For testing
if __name__ == "__main__":
    print("Testing Dynamic Lore Retrieval...")
    print("=" * 60)
    
    test_queries = [
        "Who are you?",
        "Tell me about your past",
        "What do you believe in?",
        "How do you feel about me?",
        "Tell me about yourself",
    ]
    
    for query in test_queries:
        print(f"\nQuery: \"{query}\"")
        print("-" * 40)
        lore = get_dynamic_lore(query, k=3)
        print(lore)
    
    print("\n" + "=" * 60)
