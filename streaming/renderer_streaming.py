"""
Streaming Renderer - streaming/renderer_streaming.py

Handles streaming responses from Google Gemini API with typewriter effect.
Yields tokens/chunks as they arrive for real-time display.

Shared utilities (parsing, cleaning) imported from pipeline.renderer_base.
"""

import os
import json
import sys
import time
import requests

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (Gemini API folder)
BASE_DIR = os.path.dirname(SCRIPT_DIR)

# Add parent directory to path for config import
sys.path.insert(0, BASE_DIR)
from model_config import (
    MODEL,
    TEMPERATURE,
    MAX_OUTPUT_TOKENS,
    TIMEOUT,
    FALLBACK_MESSAGE,
    API_VERSION,
)

# Import shared utilities from renderer_base (SOLID: Single Source of Truth)
from pipeline.renderer_base import (
    API_KEY,
    clean_response,
    build_gemini_payload,
)


# =============================================================================
# STREAMING RESPONSE
# =============================================================================

def stream_response(packet: str):
    """
    Stream response from Gemini API.
    Gemini streaming returns a JSON array with one object per chunk.
    
    Args:
        packet: The XML-tagged prompt packet
        
    Yields:
        String chunks as they arrive from the API
    """
    if not API_KEY:
        print("   [Error] API key not found")
        yield FALLBACK_MESSAGE
        return
    
    system_content, contents = build_gemini_payload(packet)
    
    # Use streaming endpoint
    url = f"https://generativelanguage.googleapis.com/{API_VERSION}/models/{MODEL}:streamGenerateContent?key={API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    
    data = {
        "contents": contents,
        "generationConfig": {
            "temperature": TEMPERATURE,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
        }
    }
    
    collected_texts = []
    
    try:
        response = requests.post(
            url=url,
            headers=headers,
            json=data,
            timeout=TIMEOUT,
            stream=True
        )
        response.raise_for_status()
        
        # Read the entire stream and parse as JSON array
        content = response.content.decode('utf-8')
        
        try:
            chunks = json.loads(content)
            if isinstance(chunks, list):
                for chunk_data in chunks:
                    candidates = chunk_data.get('candidates', [])
                    if candidates:
                        candidate = candidates[0]
                        # Check if finished
                        if candidate.get('finishReason'):
                            break
                        content_obj = candidate.get('content', {})
                        parts = content_obj.get('parts', [])
                        if parts:
                            text = parts[0].get('text', '')
                            if text:
                                collected_texts.append(text)
                                yield text
            elif isinstance(chunks, dict):
                # Single response (non-streaming fallback)
                candidates = chunks.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    if parts:
                        text = parts[0].get('text', '')
                        if text:
                            collected_texts.append(text)
                            yield text
                            
        except json.JSONDecodeError as e:
            print(f"   [Error] Failed to parse response: {e}")
            yield FALLBACK_MESSAGE
            return
                        
    except requests.exceptions.HTTPError as e:
        error_msg = f"[Error: HTTP {e.response.status_code if e.response else 'unknown'}]"
        print(f"   [Error] {error_msg}")
        yield FALLBACK_MESSAGE
        return
    except Exception as e:
        print(f"   [Error] {type(e).__name__}: {e}")
        yield FALLBACK_MESSAGE
        return
    
    # If no response received
    if not collected_texts:
        yield FALLBACK_MESSAGE


def render_streaming(packet: str, char_delay=0.02) -> str:
    """
    Main entry point for streaming renderer with typewriter effect.
    
    Args:
        packet: The XML-tagged prompt packet
        char_delay: Delay between characters in seconds (default 0.02 = 20ms)
        
    Returns:
        Full cleaned response string
    """
    # First, collect all chunks to detect and strip the prefix
    all_chunks = list(stream_response(packet))
    full_raw = ''.join(all_chunks)
    
    # Clean the full response to detect prefix
    cleaned_full = clean_response(full_raw)
    
    # Determine what was stripped (prefix length difference)
    prefix_len = len(full_raw) - len(cleaned_full)
    
    # Now print with typewriter effect, skipping the prefix
    chars_printed = 0
    for chunk in all_chunks:
        for char in chunk:
            chars_printed += 1
            # Skip printing if this char is part of the prefix
            if chars_printed <= prefix_len:
                continue
            # Print with delay
            sys.stdout.write(char)
            sys.stdout.flush()
            if char_delay > 0:
                time.sleep(char_delay)
    
    return cleaned_full


# Re-export FALLBACK_MESSAGE for main.py
__all__ = ['render_streaming', 'FALLBACK_MESSAGE', 'stream_response']
