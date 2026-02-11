"""
Renderer Base - pipeline/renderer_base.py

Shared utilities for all renderers (sync, streaming, summarizer).
Extracted to follow SOLID principles - Single Source of Truth.

Contains:
    - API key loading
    - Response cleaning & validation
    - XML packet parsing
    - Gemini API payload construction
"""

import os
import re
import sys

# Get the directory where this script is located (pipeline folder)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (Gemini API folder)
BASE_DIR = os.path.dirname(SCRIPT_DIR)

# Add parent directory to path for config import
sys.path.insert(0, BASE_DIR)
from model_config import (
    API_KEY_PATH,
    FALLBACK_MESSAGE,
)


# =============================================================================
# API KEY LOADING
# =============================================================================

def load_api_key():
    """Load API key from API_KEY_PATH file. Single source of truth."""
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


# Module-level API key (loaded once)
API_KEY = load_api_key()


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
# PACKET PARSING
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
