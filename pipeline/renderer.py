"""
Gemini API Renderer - Sends packets to Google Gemini/Gemma models.
Handles prompt formatting, API calls, response processing, and local caching.
"""

import os
import re
import time
import json
import hashlib
import sys
import requests

# Get the directory where this script is located (pipeline folder)
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
    MAX_RETRIES,
    FALLBACK_MESSAGE,
    CACHE_ENABLED,
    API_VERSION,
)

# Cache directory
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "ai", "responses")

def _load_api_key():
    """Load API key from API_KEY_PATH file."""
    try:
        api_key_full_path = os.path.join(BASE_DIR, API_KEY_PATH)
        with open(api_key_full_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            # Handle different formats (just key or KEY = value)
            if '=' in content:
                return content.split('=', 1)[1].strip()
            return content
    except Exception:
        pass
    return None


API_KEY = _load_api_key()


# =============================================================================
# CACHING
# =============================================================================

def _get_cache_key(system_instruction: str, user_content: str) -> str:
    """Generate cache key from system instruction and user content."""
    combined = (system_instruction + "|||" + user_content).strip().lower()
    return hashlib.md5(combined.encode()).hexdigest() + ".json"


def get_cached_response(system_instruction: str, user_content: str) -> str | None:
    """Get cached response if available."""
    if not CACHE_ENABLED:
        return None
    
    cache_path = os.path.join(CACHE_DIR, _get_cache_key(system_instruction, user_content))
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                print(f"   [Cache] Hit")
                return cache_data.get("response")
        except Exception:
            return None
    return None


def save_cached_response(system_instruction: str, user_content: str, response: str):
    """Save response to cache."""
    if not CACHE_ENABLED:
        return
    
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, _get_cache_key(system_instruction, user_content))
    try:
        cache_data = {
            "timestamp": time.time(),
            "query_preview": user_content[:60] + "..." if len(user_content) > 60 else user_content,
            "response": response
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)
    except Exception:
        pass


def clear_cache():
    """Clear all cached responses."""
    if os.path.exists(CACHE_DIR):
        import shutil
        shutil.rmtree(CACHE_DIR)
        print(f"[Cache] Cleared")


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


def validate(content: str) -> tuple[bool, str]:
    """Check response is safe and valid."""
    content = content.strip()
    
    if not content or len(content) < 2:
        return False, "Too short"
    
    if content.startswith(("[User]:", "User:")) or "\n[User]:" in content:
        return False, "User impersonation"
    
    return True, ""


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
    """
    Build Gemini API payload from XML-tagged packet.
    
    Returns:
        Tuple of (system_content, contents_list)
    """
    sections = parse_sections(packet)
    
    # Build system content (will be combined with first user message for Gemma)
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
    
    # For Gemma models, combine system with user content
    combined_content = f"{system_content}\n\n{user_content}"
    
    contents = [
        {
            "role": "user",
            "parts": [{"text": combined_content}]
        }
    ]
    
    return system_content, contents


def get_response(system_content: str, contents: list) -> str:
    """Send to Gemini API with retries."""
    if not API_KEY:
        print("   [Error] API key not found")
        return FALLBACK_MESSAGE
    
    url = f"https://generativelanguage.googleapis.com/{API_VERSION}/models/{MODEL}:generateContent?key={API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    
    data = {
        "contents": contents,
        "generationConfig": {
            "temperature": TEMPERATURE,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
        }
    }
    
    for attempt in range(1, MAX_RETRIES + 1):
        #print(f"   >> Attempt {attempt}/{MAX_RETRIES}...")
        
        try:
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
            if not candidates:
                print("   [Warn] No candidates in response")
                time.sleep(0.5 * attempt)
                continue
            
            parts = candidates[0].get('content', {}).get('parts', [])
            if not parts:
                print("   [Warn] No parts in response")
                time.sleep(0.5 * attempt)
                continue
            
            raw_content = parts[0].get('text', '').strip()
            
            if not raw_content:
                print("   [Warn] Empty response from API")
                time.sleep(0.5 * attempt)
                continue
            
            # Log raw response preview
            debug_preview = raw_content[:150].replace('\n', ' | ')
            #print(f"   [Raw] {debug_preview}...")
            
            # Clean the response
            content = clean_response(raw_content)
            
            # Log cleaned response preview
            cleaned_preview = content[:80].replace('\n', ' | ') if content else "(empty)"
            #print(f"   [Response] {cleaned_preview}...")
            
            # Validate
            is_valid, reason = validate(content)
            if is_valid:
                return content
            
            print(f"   [Warn] Validation failed: {reason}, retrying...")
            time.sleep(0.3 * attempt)
            
        except requests.exceptions.HTTPError as e:
            print(f"   [Warn] HTTP Error: {e}")
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"   [Detail] {error_detail.get('error', {}).get('message', 'Unknown error')}")
                except:
                    pass
            time.sleep(0.5 * attempt)
        except Exception as e:
            print(f"   [Warn] {type(e).__name__}: {e}")
            time.sleep(0.5 * attempt)
    
    return FALLBACK_MESSAGE


def render(packet: str) -> str:
    """Main entry point."""
    system_content, contents = build_gemini_payload(packet)
    
    # Extract user content for cache key
    user_content = contents[0]["parts"][0]["text"] if contents else ""
    
    # Check cache first
    cached = get_cached_response(system_content, user_content)
    if cached:
        return cached
    
    # Make API call
    # print(f"   >> Sending to {MODEL} (Gemini API)...")
    response = get_response(system_content, contents)
    
    # Cache successful responses
    if response and response != FALLBACK_MESSAGE and not response.startswith("[Error"):
        save_cached_response(system_content, user_content, response)
    
    return response
