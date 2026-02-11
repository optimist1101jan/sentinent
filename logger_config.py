"""
Logger Configuration - Markdown Table-Based Activity Log

Writes a Priority Dashboard log to data/system_logs/Log_Files.md with:
  - Table format: | Priority | Status | Timestamp | Module | Message |
  - Severity: LOW (🔵 DEBUG), MEDIUM (🟢 INFO / 🟡 WARNING), HIGH (🔴 ERROR)
  - Module icons: 🪄 LLM/API, 🧠 Memory, ⚙️ System, ✅ Success, 🛡️ Safety
  - Rotating file handler (5MB, 3 backups)

Usage in any module:
    from logger_config import get_logger
    logger = get_logger(__name__)
    logger.info("Memory retrieval success - Found 3 vectors in FAISS")
"""

import os
import atexit
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

# =============================================================================
# PATHS
# =============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "data", "system_logs")
LOG_FILE = os.path.join(LOG_DIR, "Log_Files.md")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# =============================================================================
# TABLE HEADER (written at file creation and rotation)
# =============================================================================

TABLE_HEADER = (
    "| Priority | Status | Date | Timestamp | Module | Message |\n"
    "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
)

# =============================================================================
# MODULE ICON MAPPING
# =============================================================================

# Maps source filenames to module icons
MODULE_ICONS = {
    # 🪄 LLM / API — the magic happens here
    "renderer_streaming.py": "🪄",
    "renderer.py":           "🪄",
    "renderer_base.py":      "🪄",
    "model_config.py":       "🪄",
    "summarizer_builder.py": "🪄",
    
    # 🧠 Memory — FAISS and SQLite retrievals
    "memory.py":             "🧠",
    "memory_loader.py":      "🧠",
    "semantic_search.py":    "🧠",
    
    # ⚙️ System — orchestration and utilities
    "main.py":               "⚙️",
    "logger_config.py":      "⚙️",
    "packet_builder.py":     "⚙️",
    "temporal.py":           "⚙️",
    "conversation.py":       "⚙️",
    
    # 🛡️ Safety — proximity and guardrails
    "proximity_manager.py":  "🛡️",
}


# =============================================================================
# CUSTOM TABLE FORMATTER
# =============================================================================

class TableFormatter(logging.Formatter):
    """
    Formats log records as Markdown table rows.
    
    Output example:
        | LOW | 🔵 | `14:26:37.659` | 🧠 `semantic_search.py` | Scanning vector DB for "Hi" |
        | MEDIUM | 🟢 | `14:26:35.569` | ⚙️ `main.py` | System initialized |
        | HIGH | 🔴 | `14:27:10.122` | 🪄 `model_config.py` | API Key Expired |
    """
    
    SEVERITY_MAP = {
        "DEBUG":    ("LOW",    "🔵"),
        "INFO":     ("MEDIUM", "🟢"),
        "WARNING":  ("MEDIUM", "🟡"),
        "ERROR":    ("HIGH",   "🔴"),
        "CRITICAL": ("HIGH",   "💀"),
    }
    
    def format(self, record):
        # Timestamp: 12-hour format with AM/PM and milliseconds
        dt = datetime.fromtimestamp(record.created)
        timestamp = dt.strftime("%I:%M:%S")
        ampm = dt.strftime("%p")
        ms = f"{int(record.msecs):03d}"
        date_str = dt.strftime("%Y-%m-%d")
        
        # Severity and status icon
        priority, status_icon = self.SEVERITY_MAP.get(record.levelname, ("LOW", "⚪"))
        
        # Module icon based on source filename
        module_icon = MODULE_ICONS.get(record.filename, "⚙️")
        
        # Clean message (escape pipes for table safety)
        message = record.getMessage().replace("|", "∣")
        
        # Add exception info inline if present
        if record.exc_info and record.exc_info[1]:
            import traceback
            tb = "".join(traceback.format_exception(*record.exc_info))
            # Collapse to single line for table
            tb_short = tb.strip().split("\n")[-1]
            message = f"{message} — `{tb_short}`"
        
        # Build table row
        row = f"| {priority} | {status_icon} | `{date_str}` | `{timestamp}.{ms} {ampm}` | {module_icon} `{record.filename}` | {message} |"
        return row


# =============================================================================
# CONSOLE FORMATTER (minimal, doesn't clutter CLI)
# =============================================================================

class ConsoleFormatter(logging.Formatter):
    """Minimal console format — only shows warnings and errors."""
    
    LEVEL_EMOJI = {
        "WARNING":  "🟡",
        "ERROR":    "🔴",
        "CRITICAL": "💀",
    }
    
    def format(self, record):
        emoji = self.LEVEL_EMOJI.get(record.levelname, "")
        return f"   {emoji} [{record.levelname}] {record.getMessage()}"


# =============================================================================
# CUSTOM ROTATING HANDLER (writes table header on new files)
# =============================================================================

class TableRotatingHandler(RotatingFileHandler):
    """
    RotatingFileHandler that writes the Markdown table header
    at the top of every new/rotated log file.
    """
    
    def _open(self):
        """Override to write table header when a new file is opened."""
        stream = super()._open()
        # If file is empty (new or just rotated), write the header
        stream.seek(0, 2)  # Seek to end
        if stream.tell() == 0:
            stream.write(TABLE_HEADER)
            stream.flush()
        return stream


# =============================================================================
# LOGGER SETUP
# =============================================================================

_initialized = False

def _setup_root_logger():
    """Configure the root 'SentientLog' logger once."""
    global _initialized
    if _initialized:
        return
    
    root_logger = logging.getLogger("SentientLog")
    root_logger.setLevel(logging.DEBUG)
    
    # --- File Handler (Markdown table log) ---
    file_handler = TableRotatingHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(TableFormatter())
    root_logger.addHandler(file_handler)
    
    # --- Console Handler (warnings/errors only) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(ConsoleFormatter())
    root_logger.addHandler(console_handler)
    
    # --- Shutdown Hook: always log session end, even on Ctrl+C ---
    atexit.register(log_session_end)
    
    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger under the 'SentientLog' namespace.
    
    Args:
        name: Module name (use __name__)
        
    Returns:
        Logger instance ready to use
        
    Usage:
        from logger_config import get_logger
        logger = get_logger(__name__)
        logger.info("Everything OK")
        logger.error("API Failed - Model: gemma-3-12b-it - Status: 429")
    """
    _setup_root_logger()
    return logging.getLogger(f"SentientLog.{name}")


def log_session_start():
    """Write a session separator row to mark the start of a new session."""
    _setup_root_logger()
    logger = logging.getLogger("SentientLog")
    
    for handler in logger.handlers:
        if isinstance(handler, TableRotatingHandler):
            now = datetime.now()
            separator = (
                f"| **---** | **🤖** | `{now.strftime('%Y-%m-%d')}` | **`{now.strftime('%I:%M:%S %p')}`** | **SESSION** | "
                f"**🤖 Sentient Activity Log — Session Start** |\n"
            )
            handler.stream.write(separator)
            handler.stream.flush()
            break


_session_ended = False

def log_session_end():
    """Write a session end marker row. Guarded against duplicate calls."""
    global _session_ended
    if _session_ended:
        return
    _session_ended = True
    
    _setup_root_logger()
    logger = logging.getLogger("SentientLog")
    
    for handler in logger.handlers:
        if isinstance(handler, TableRotatingHandler):
            now = datetime.now()
            separator = (
                f"| **---** | **🏁** | `{now.strftime('%Y-%m-%d')}` | **`{now.strftime('%I:%M:%S %p')}`** | **SESSION** | "
                f"**Session closed** |\n"
            )
            handler.stream.write(separator)
            handler.stream.flush()
            break
