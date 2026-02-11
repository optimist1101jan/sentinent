"""
Model Configuration - Central place to configure LLM settings
Using Google Gemini API
"""

import json
import requests

from logger_config import get_logger
logger = get_logger(__name__)

# =============================================================================
# MODEL SELECTION - Google Gemini / Gemma Models
# =============================================================================

# Available models (Google AI Studio / Gemini API):
#   - "gemma-3-1b-it"
#   - "gemma-3-4b-it"  
#   - "gemma-3-12b-it"
#   - "gemma-3-27b-it"
#   - "gemini-2.0-flash"
#   - "gemini-2.0-flash-lite"
#   - "gemini-2.5-flash"
#   - "gemini-2.5-pro"

MODEL = "gemma-3-12b-it"

# =============================================================================
# GENERATION PARAMETERS
# =============================================================================

TEMPERATURE = 0.7
MAX_OUTPUT_TOKENS = 1000

# =============================================================================
# API SETTINGS - Google Gemini API
# =============================================================================

API_KEY_PATH = "API_KEY.txt"
API_VERSION = "v1beta"
API_URL = f"https://generativelanguage.googleapis.com/{API_VERSION}/models/{MODEL}:generateContent"

# Request timeout in seconds
TIMEOUT = 60

# Number of retries on failure
MAX_RETRIES = 3

# =============================================================================
# SYSTEM BEHAVIOR
# =============================================================================

FALLBACK_MESSAGE = "*AI looks at you, seemingly lost in a daydream, and doesn't respond.*"

# Cache configuration
CACHE_ENABLED = True


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_api_key():
    """Load API key from file."""
    try:
        with open(API_KEY_PATH, 'r') as f:
            content = f.read().strip()
            # Handle different formats (just key or KEY = value)
            if '=' in content:
                return content.split('=', 1)[1].strip()
            return content
    except Exception as e:
        logger.error(f"Failed to load API key from {API_KEY_PATH}: {e}")
        print(f"Error loading API key: {e}")
        return None


def generate_response(messages, temperature=None, max_tokens=None):
    """
    Generate a response using Google Gemini API.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        temperature: Optional override for temperature
        max_tokens: Optional override for max tokens
    
    Returns:
        Generated text response or None on failure
    """
    api_key = load_api_key()
    if not api_key:
        return None
    
    # Convert messages to Gemini format
    contents = []
    system_instruction = None
    
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        
        if role == 'system':
            # Gemma models don't support system_instruction, combine with first user message
            system_instruction = content
        elif role == 'user':
            if system_instruction:
                content = f"{system_instruction}\n\n{content}"
                system_instruction = None
            contents.append({
                "role": "user",
                "parts": [{"text": content}]
            })
        elif role == 'assistant':
            contents.append({
                "role": "model",
                "parts": [{"text": content}]
            })
    
    # Build request URL with API key
    url = f"https://generativelanguage.googleapis.com/{API_VERSION}/models/{MODEL}:generateContent?key={api_key}"
    
    data = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature if temperature is not None else TEMPERATURE,
            "maxOutputTokens": max_tokens if max_tokens is not None else MAX_OUTPUT_TOKENS,
        }
    }
    
    try:
        response = requests.post(
            url=url,
            headers={"Content-Type": "application/json"},
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
                return parts[0].get('text', '')
        return None
    except Exception as e:
        logger.error(f"generate_response failed - {type(e).__name__}: {e}", exc_info=True)
        print(f"Error generating response: {e}")
        return None


def generate_single_prompt(prompt, system_prompt=None):
    """
    Generate a response from a single prompt string.
    
    Args:
        prompt: The user prompt
        system_prompt: Optional system prompt
    
    Returns:
        Generated text response or None on failure
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return generate_response(messages)
