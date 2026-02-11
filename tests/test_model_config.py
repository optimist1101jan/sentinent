"""
TEST: model_config.py — Layer 1 (Core)

What we're testing:
    - Constants exist and have correct types/values
    - load_api_key() reads key from file correctly
    - load_api_key() handles missing file
    - load_api_key() handles KEY=VALUE format
    - generate_response() builds correct Gemini payload (mocked API)
    - generate_response() handles API failure gracefully

How to run:
    pytest tests/test_model_config.py -v

The test file is heavily commented so you can read through it and understand the pattern:
Tests 1-7: Constants validation (does MODEL exist? is TEMPERATURE in range?)
Tests 8-11: load_api_key() — plain key, KEY=value format, whitespace, missing file
Tests 12-16: generate_response() — mocked API success, no key, network error, empty candidates, system message merging
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock

# Add project root to path so we can import model_config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import model_config


# =============================================================================
# TEST 1: Constants exist and have correct types
# =============================================================================
# WHY: If someone accidentally changes MODEL to an integer or deletes
#       TEMPERATURE, everything downstream breaks silently.

def test_model_name_is_string():
    """MODEL should be a non-empty string."""
    assert isinstance(model_config.MODEL, str)
    assert len(model_config.MODEL) > 0


def test_temperature_in_valid_range():
    """TEMPERATURE should be between 0.0 and 2.0 (Gemini API range)."""
    assert isinstance(model_config.TEMPERATURE, float)
    assert 0.0 <= model_config.TEMPERATURE <= 2.0


def test_max_tokens_is_positive():
    """MAX_OUTPUT_TOKENS should be a positive integer."""
    assert isinstance(model_config.MAX_OUTPUT_TOKENS, int)
    assert model_config.MAX_OUTPUT_TOKENS > 0


def test_timeout_is_reasonable():
    """TIMEOUT should be between 5 and 300 seconds."""
    assert isinstance(model_config.TIMEOUT, int)
    assert 5 <= model_config.TIMEOUT <= 300


def test_max_retries_is_reasonable():
    """MAX_RETRIES should be between 1 and 10."""
    assert isinstance(model_config.MAX_RETRIES, int)
    assert 1 <= model_config.MAX_RETRIES <= 10


def test_api_url_contains_model():
    """API_URL should reference the selected MODEL."""
    assert model_config.MODEL in model_config.API_URL


def test_fallback_message_is_string():
    """FALLBACK_MESSAGE should be a non-empty string."""
    assert isinstance(model_config.FALLBACK_MESSAGE, str)
    assert len(model_config.FALLBACK_MESSAGE) > 0


# =============================================================================
# TEST 2: load_api_key() — reading the key from file
# =============================================================================
# WHY: If this breaks, EVERY API call in the project fails.
#       We mock the file so we don't need a real API key to test.

def test_load_api_key_plain_format():
    """load_api_key() should read a plain API key from file."""
    fake_key = "AIzaSyD_fake_key_12345"
    with patch("builtins.open", mock_open(read_data=fake_key)):
        result = model_config.load_api_key()
    assert result == fake_key


def test_load_api_key_equals_format():
    """load_api_key() should handle 'KEY = value' format."""
    with patch("builtins.open", mock_open(read_data="API_KEY = AIzaSyD_fake_key_12345")):
        result = model_config.load_api_key()
    assert result == "AIzaSyD_fake_key_12345"


def test_load_api_key_strips_whitespace():
    """load_api_key() should strip leading/trailing whitespace."""
    with patch("builtins.open", mock_open(read_data="  AIzaSyD_fake_key_12345  \n")):
        result = model_config.load_api_key()
    assert result == "AIzaSyD_fake_key_12345"


def test_load_api_key_missing_file():
    """load_api_key() should return None if file doesn't exist."""
    with patch("builtins.open", side_effect=FileNotFoundError()):
        result = model_config.load_api_key()
    assert result is None


# =============================================================================
# TEST 3: generate_response() — API interaction (MOCKED)
# =============================================================================
# WHY: We're NOT calling the real API. We mock requests.post to simulate
#       what Gemini would return. This tests OUR code, not Google's.

def test_generate_response_success():
    """generate_response() should extract text from a valid Gemini response."""
    # This is what Gemini API actually returns
    fake_api_response = {
        "candidates": [{
            "content": {
                "parts": [{"text": "Hello! How can I help you?"}]
            }
        }]
    }

    mock_response = MagicMock()
    mock_response.json.return_value = fake_api_response
    mock_response.raise_for_status.return_value = None

    with patch("model_config.load_api_key", return_value="fake_key"):
        with patch("requests.post", return_value=mock_response):
            result = model_config.generate_response([
                {"role": "user", "content": "Hello"}
            ])

    assert result == "Hello! How can I help you?"


def test_generate_response_no_api_key():
    """generate_response() should return None if no API key."""
    with patch("model_config.load_api_key", return_value=None):
        result = model_config.generate_response([
            {"role": "user", "content": "Hello"}
        ])
    assert result is None


def test_generate_response_api_failure():
    """generate_response() should return None on network error."""
    with patch("model_config.load_api_key", return_value="fake_key"):
        with patch("requests.post", side_effect=Exception("Connection timeout")):
            result = model_config.generate_response([
                {"role": "user", "content": "Hello"}
            ])
    assert result is None


def test_generate_response_empty_candidates():
    """generate_response() should return None if API returns no candidates."""
    fake_api_response = {"candidates": []}

    mock_response = MagicMock()
    mock_response.json.return_value = fake_api_response
    mock_response.raise_for_status.return_value = None

    with patch("model_config.load_api_key", return_value="fake_key"):
        with patch("requests.post", return_value=mock_response):
            result = model_config.generate_response([
                {"role": "user", "content": "Hello"}
            ])

    assert result is None


def test_generate_response_system_message_merged():
    """System messages should be merged with the first user message."""
    captured_data = {}

    def capture_post(*args, **kwargs):
        captured_data["body"] = json.loads(kwargs.get("data", "{}"))
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}]
        }
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    with patch("model_config.load_api_key", return_value="fake_key"):
        with patch("requests.post", side_effect=capture_post):
            model_config.generate_response([
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hi"}
            ])

    # System content should be merged into the user message
    user_text = captured_data["body"]["contents"][0]["parts"][0]["text"]
    assert "You are helpful." in user_text
    assert "Hi" in user_text
