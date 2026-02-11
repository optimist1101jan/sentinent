"""
Memory Loader Module - memory/memory_loader.py

Handles memory intent detection and fetching from episodic (SQLite) and semantic (FAISS) sources.
Called by packet_builder when memory-related intent is detected.
"""

import re
import sys
import os

# Add parent directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BASE_DIR)

from agent.memory import MemoryStore
from agent.semantic_search import search as semantic_search

from logger_config import get_logger
logger = get_logger(__name__)


class MemoryLoader:
    """Handles memory retrieval based on user intent."""
    
    def __init__(self):
        self.memory_store = MemoryStore()
    
    @staticmethod
    def is_memory_intent(user_input: str) -> bool:
        """
        Detect if user is asking about memories or past events.
        Returns True if memory bank should be included.
        """
        text = user_input.lower().strip()
        
        # Memory-related keywords and phrases
        memory_indicators = [
            r'\bremember\b', r'\brecall\b', r'\bremind\b',
            r'\bdo you remember\b', r'\bdo you recall\b',
            r'\bremember when\b', r'\bthat time\b', r'\bthe other day\b',
            r'\blast time\b', r'\bwe talked about\b', r'\bwe discussed\b',
            r'\byou said\b', r'\byou told me\b', r'\byou mentioned\b',
            r'\bwhat happened\b', r'\bwhat did we\b', r'\bwhen we\b',
            r'\btell me about\b', r'\bhow was\b', r'\bwhat was\b',
            r'\bdid you say\b', r'\bdid we\b', r'\bhave you\b.*\bforgotten\b',
            r'\bforget\b', r'\bforgot\b', r'\bwhat about\b',
        ]
        
        for pattern in memory_indicators:
            if re.search(pattern, text):
                logger.debug(f"Memory intent detected - Pattern: {pattern} - Input: \"{text[:60]}\"")
                return True
        
        return False
    
    @staticmethod
    def format_memories(memories: list, max_length: int = 150) -> str:
        """
        Format memory strings as bullet points.
        
        Args:
            memories: List of memory strings
            max_length: Max length for each bullet
            
        Returns:
            Formatted bullet list string
        """
        if not memories:
            return "- No specific memories retrieved."
        
        bullets = []
        for mem in memories:
            text = mem.replace("\n", " ").strip()
            if len(text) > max_length:
                text = text[:max_length].rsplit(" ", 1)[0] + "..."
            bullets.append(f"- {text}")
        
        return "\n".join(bullets)
    
    def fetch_memories(self, user_input: str, episodic_limit: int = 3, semantic_limit: int = 5) -> str:
        """
        Fetch memories from both episodic and semantic sources.
        
        Args:
            user_input: The user's query
            episodic_limit: Max episodic memories to retrieve
            semantic_limit: Max semantic memories to retrieve
            
        Returns:
            Formatted memory section for packet
        """
        # Search episodic memory (SQLite FTS5)
        episodes = self.memory_store.search(user_input, limit=episodic_limit)
        
        # Search semantic memory (FAISS)
        semantic_results = semantic_search(user_input, k=semantic_limit)
        
        # Combine and deduplicate
        relevant_memories = []
        
        if semantic_results:
            for source, text, score in semantic_results[:3]:
                relevant_memories.append(text)
        
        if episodes:
            for ep in episodes[:2]:
                if ep not in relevant_memories:
                    relevant_memories.append(ep)
        
        # Format as bullet points
        memories_block = self.format_memories(relevant_memories)
        logger.info(f"Memory retrieval success - Found {len(relevant_memories)} memories (episodic: {len(episodes) if episodes else 0}, semantic: {len(semantic_results) if semantic_results else 0})")
        
        return f"""<memory_bank>
Use from this memory block only if required.
{memories_block}
</memory_bank>

"""
    
    def get_memory_section(self, user_input: str) -> str:
        """
        Get formatted memory section if intent is detected, otherwise empty string.
        
        Args:
            user_input: The user's input message
            
        Returns:
            Memory section XML or empty string
        """
        if not self.is_memory_intent(user_input):
            return ""
        
        logger.info(f"Fetching memories for: \"{user_input[:60]}\"")
        return self.fetch_memories(user_input)
    
    def close(self):
        """Close database connections."""
        self.memory_store.close()


# Convenience function for direct usage
def get_memory_section(user_input: str) -> str:
    """
    Get memory section for packet if user input indicates memory intent.
    
    Args:
        user_input: The user's input message
        
    Returns:
        Formatted memory section or empty string
    """
    loader = MemoryLoader()
    section = loader.get_memory_section(user_input)
    loader.close()
    return section


if __name__ == "__main__":
    # Test the memory loader
    loader = MemoryLoader()
    
    test_inputs = [
        "hi",
        "do you remember when we went to the park?",
        "what did we talk about yesterday?",
        "tell me about our trip",
    ]
    
    print("Testing MemoryLoader:")
    print("=" * 60)
    for text in test_inputs:
        is_memory = loader.is_memory_intent(text)
        print(f"\nInput: \"{text}\"")
        print(f"Memory intent: {is_memory}")
        if is_memory:
            section = loader.get_memory_section(text)
            print(f"Memory section preview:\n{section[:300]}...")
    
    loader.close()
