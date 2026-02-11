"""
Summarizer Builder - pipeline/summarizer_builder.py

Stage 2 & 3: The Summarizer Pipeline + Real-Time Long-Term Indexing
Handles compression of 5-turn conversation cycles and immediate indexing.
Uses Google Gemini API for summarization.
"""

import os
import requests
import json
import sys

# Get the directory where this script is located (pipeline folder)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (Gemini API folder)
BASE_DIR = os.path.dirname(SCRIPT_DIR)

# Add parent directory to path for imports
sys.path.insert(0, BASE_DIR)
from agent.memory import MemoryStore
from agent.semantic_search import add_chunk_to_index
from model_config import (
    MODEL,
    API_VERSION,
    TIMEOUT,
)

# Import shared API key loader (SOLID: Single Source of Truth)
from pipeline.renderer_base import API_KEY

from logger_config import get_logger
logger = get_logger(__name__)

TEMPERATURE = 0.3  # Lower temperature for factual summarization
MAX_TOKENS = 256

SUMMARIZER_PROMPT = """Summarize the following 5 turns into a single, objective sentence for long-term storage. Focus on facts, preferences, and emotional shifts."""


def build_summarizer_packet(raw_conversation_text: str) -> str:
    """
    Build the summarizer.md packet for the 5-turn cycle.
    
    Args:
        raw_conversation_text: The buffered conversation (5 turns)
        
    Returns:
        Formatted packet text for the summarizer
    """
    packet = (
        "=== SYSTEM ===\n"
        "You are a memory compression system. Create concise, factual summaries.\n\n"
        
        "=== INSTRUCTION ===\n"
        f"{SUMMARIZER_PROMPT}\n\n"
        
        "=== CONVERSATION TO SUMMARIZE ===\n"
        f"{raw_conversation_text}\n\n"
        
        "=== OUTPUT FORMAT ===\n"
        "Provide exactly one sentence capturing the key information."
    )
    
    return packet


def save_summarizer_packet(packet_text: str, output_path: str = None):
    """
    Save the summarizer packet to disk.
    
    Args:
        packet_text: The formatted packet
        output_path: Where to save (default: pipeline/summarizer.md)
    """
    if output_path is None:
        output_path = os.path.join(SCRIPT_DIR, "summarizer.md")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(packet_text)


def summarize_with_llm(raw_conversation_text: str) -> str:
    """
    Execute inference to compress 5 turns into a single memory sentence.
    Uses Google Gemini API.
    
    Args:
        raw_conversation_text: The buffered conversation from buffer_to_raw_text()
        
    Returns:
        compressed_memory: The 1-sentence summary for long-term storage
    """
    if not API_KEY:
        logger.error("API key not found - Cannot summarize")
        return "[Error: API key not found]"
    
    url = f"https://generativelanguage.googleapis.com/{API_VERSION}/models/{MODEL}:generateContent?key={API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    
    # Build content for Gemini (combine system + user for Gemma models)
    prompt = (
        "You are a memory compression system. Create concise, factual summaries for long-term storage. "
        "Always respond with exactly one sentence focusing on facts, preferences, and emotional shifts.\n\n"
        f"Summarize the following 5 turns into a single, objective sentence for long-term storage:\n\n"
        f"{raw_conversation_text}"
    )
    
    data = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": TEMPERATURE,
            "maxOutputTokens": MAX_TOKENS,
        }
    }
    
    try:
        logger.info(f"Summarization started - Model: {MODEL} - Input: {len(raw_conversation_text)} chars")
        print(f"   >> Sending to Gemini for summarization ({MODEL})...")
        response = requests.post(
            url=url,
            headers=headers,
            data=json.dumps(data),
            timeout=TIMEOUT
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Extract text from Gemini response format
        candidates = result.get('candidates', [])
        if candidates:
            parts = candidates[0].get('content', {}).get('parts', [])
            if parts:
                content = parts[0].get('text', '').strip()
                # Ensure it's a single sentence (basic cleanup)
                content = content.replace("\n", " ").strip()
                logger.info(f"Summarization success - Output: \"{content[:100]}\"")
                return content
        
        return "[Error: No summary generated]"
            
    except requests.exceptions.ConnectionError:
        logger.error("Summarization failed - Cannot connect to Gemini API")
        return "[Error: Cannot connect to Gemini API for summarization]"
    except requests.exceptions.Timeout:
        logger.error(f"Summarization failed - Request timed out ({TIMEOUT}s)")
        return "[Error: Summarization request timed out]"
    except requests.exceptions.HTTPError as e:
        error_msg = str(e)
        if e.response is not None:
            try:
                error_detail = e.response.json()
                error_msg = error_detail.get('error', {}).get('message', str(e))
            except:
                pass
        return f"[Error: {error_msg}]"
    except Exception as e:
        logger.error(f"Summarization failed - {type(e).__name__}: {e}", exc_info=True)
        return f"[Error during summarization: {str(e)}]"


def index_compressed_memory(compressed_memory: str, cycle_num: int = 0):
    """
    Stage 3: Burn compressed memory into permanent storage.
    
    Args:
        compressed_memory: The 1-sentence summary from LLM
        cycle_num: Optional cycle identifier
        
    Returns:
        dict: Status of indexing operations
    """
    results = {"episodic": False, "semantic": False}
    
    # 1. Add to episodic memory (SQLite brain.db)
    try:
        memory_store = MemoryStore()
        source = f"summarizer_cycle_{cycle_num:03d}"
        rowid = memory_store.add_episode(compressed_memory, source=source)
        memory_store.close()
        print(f"   >> [Episodic] Added to brain.db (rowid: {rowid})")
        logger.info(f"Episodic index success - brain.db rowid: {rowid} - Source: {source}")
        results["episodic"] = True
    except Exception as e:
        logger.error(f"Episodic index failed - {e}")
        print(f"   >> [Episodic] Error: {e}")
    
    # 2. Add to semantic memory (FAISS index)
    try:
        add_chunk_to_index(compressed_memory, source=f"summarizer/cycle_{cycle_num:03d}")
        print(f"   >> [Semantic] Added to FAISS index")
        logger.info(f"Semantic index success - FAISS chunk added - Cycle: {cycle_num}")
        results["semantic"] = True
    except Exception as e:
        logger.error(f"Semantic index failed - {e}")
        print(f"   >> [Semantic] Error: {e}")
    
    return results


def run_summarizer_pipeline(raw_conversation_text: str, save_packet: bool = True, cycle_num: int = 0) -> str:
    """
    Stage 2 & 3 Complete Pipeline: 
    - Build packet, save to file, execute inference (Stage 2)
    - Index compressed memory into long-term storage (Stage 3)
    
    Args:
        raw_conversation_text: The 5-turn conversation from buffer
        save_packet: Whether to save the packet to pipeline/summarizer.md
        cycle_num: Optional cycle identifier for indexing
        
    Returns:
        compressed_memory: The 1-sentence summary for long-term storage
    """
    # Stage 2 - Step 1: Build the packet
    packet = build_summarizer_packet(raw_conversation_text)
    
    # Stage 2 - Step 2: Save to pipeline/summarizer.md
    if save_packet:
        save_summarizer_packet(packet)
        print("   >> Summarizer packet saved to pipeline/summarizer.md")
    
    # Stage 2 - Step 3: Execute inference
    compressed_memory = summarize_with_llm(raw_conversation_text)
    
    # Stage 3: Real-Time Long-Term Indexing
    if compressed_memory and not compressed_memory.startswith("[Error"):
        print("   >> Indexing compressed memory...")
        index_compressed_memory(compressed_memory, cycle_num=cycle_num)
    else:
        logger.warning(f"Indexing skipped - Response was error/empty: \"{compressed_memory[:60] if compressed_memory else 'None'}\"")
        print("   >> [Indexing] Skipped due to empty/error response")
        if not compressed_memory:
            print("   >> [Warning] LLM returned empty summary")
    
    return compressed_memory


if __name__ == "__main__":
    # Test the summarizer builder
    test_conversation = """USER: Hello, how are you today?
AI: I'm doing wonderfully, thank you for asking! The weather is quite nice.
USER: I'm feeling a bit stressed about work.
AI: Oh no, work stress is the worst. Want to talk about it?
USER: My boss gave me an impossible deadline.
AI: That sounds really frustrating. You should take a break.
USER: Yeah, maybe I'll go for a walk later.
AI: A walk sounds perfect! Fresh air always helps clear the mind."""
    
    print("Testing summarizer pipeline...")
    result = run_summarizer_pipeline(test_conversation)
    print(f"\nCompressed Memory: {result}")
