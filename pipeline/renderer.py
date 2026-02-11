"""
Gemini API Renderer - Sends packets to Google Gemini/Gemma models.
Handles caching and synchronous API calls with retries.

Shared utilities (parsing, cleaning, validation) imported from renderer_base.py.
"""

import os
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
    TEMPERATURE,
    MAX_OUTPUT_TOKENS,
    TIMEOUT,
    MAX_RETRIES,
    FALLBACK_MESSAGE,
    CACHE_ENABLED,
    API_VERSION,
)

# Import shared utilities from renderer_base (SOLID: Single Source of Truth)
from pipeline.renderer_base import (
    API_KEY,
    clean_response,
    validate,
    build_gemini_payload,
)


# =============================================================================
# CACHING
# =============================================================================

# Cache directory
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "ai", "responses")


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
# API CALL WITH RETRIES
# =============================================================================

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
            
            # Clean the response
            content = clean_response(raw_content)
            
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


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

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
    response = get_response(system_content, contents)
    
    # Cache successful responses
    if response and response != FALLBACK_MESSAGE and not response.startswith("[Error"):
        save_cached_response(system_content, user_content, response)
    
    return response
