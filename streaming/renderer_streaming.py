"""
Streaming Renderer - streaming/renderer_streaming.py

Handles streaming responses from Google Gemini API with typewriter effect.
Yields tokens/chunks as they arrive for real-time display.
"""

import os
import re
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
    API_KEY_PATH,
    TEMPERATURE,
    MAX_OUTPUT_TOKENS,
    TIMEOUT,
    FALLBACK_MESSAGE,
    API_VERSION,
)

def _load_api_key():
    """Load API key from API_KEY_PATH file."""
    try:
        api_key_full_path = os.path.join(BASE_DIR, API_KEY_PATH)
        with open(api_key_full_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if '=' in content:
                return content.split('=', 1)[1].strip()
            return content
    except Exception:
        pass
    return None


API_KEY = _load_api_key()


# =============================================================================
# CLEANING & VALIDATION
# =============================================================================

def clean_response(content: str) -> str:
    """Clean and format the final response."""
    # Remove [AI] prefixes if model added them
    for prefix in ["[AI]:", "[AI],", "[AI]", "AI:"]:
        if content.startswith(prefix):
            content = content[len(prefix):].strip()
    
    # Strip leading punctuation artifacts
    content = content.lstrip('.:,;- ').strip()
    
    return content


# =============================================================================
# PAYLOAD BUILDING
# =============================================================================

def parse_sections(packet: str) -> dict:
    """Parse XML tags from packet."""
    sections = {}
    xml_pattern = r'<(system_directive|persona|lore|context|temporal_data|memory_bank|chat_history|user_input|trigger|distance_context)>(.*?)</\1>'
    for match in re.finditer(xml_pattern, packet, re.DOTALL | re.IGNORECASE):
        sections[match.group(1).lower()] = match.group(2).strip()
    return sections


def build_gemini_payload(packet: str) -> tuple[str, list]:
    """Build Gemini API payload from XML-tagged packet."""
    sections = parse_sections(packet)
    
    # Build system content
    system_parts = []
    if "system_directive" in sections:
        system_parts.append(sections["system_directive"])
    
    context_parts = []
    if "temporal_data" in sections:
        context_parts.append(f"Time:\n{sections['temporal_data']}")
    if "distance_context" in sections:
        context_parts.append(f"Context:\n{sections['distance_context']}")
    if "memory_bank" in sections:
        context_parts.append(f"Memories:\n{sections['memory_bank']}")
    if "chat_history" in sections:
        context_parts.append(f"History:\n{sections['chat_history']}")
    
    if context_parts:
        system_parts.append("\n".join(context_parts))
    
    system_parts.append("\nRespond as AI. Start with [AI]:")
    system_content = '\n'.join(system_parts)
    
    # Build user message
    user_content = sections.get("user_input", "")
    if "trigger" in sections:
        user_content += "\n\n" + sections["trigger"]
    
    combined_content = f"{system_content}\n\n{user_content}"
    
    contents = [
        {
            "role": "user",
            "parts": [{"text": combined_content}]
        }
    ]
    
    return system_content, contents


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
