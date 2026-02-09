import os
from datetime import datetime

# Get the directory where this script is located (agent folder)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (Gemini API folder)
BASE_DIR = os.path.dirname(SCRIPT_DIR)

LOG_DIR = os.path.join(BASE_DIR, "data", "logs_raw")
BUFFER_DIR = os.path.join(BASE_DIR, "data", "buffer")

# =============================================================================
# SESSION MANAGEMENT
# =============================================================================
# Each conversation session gets its own file.
# A new session starts when the program launches.

_current_session_file = None  # Track the current session file

# =============================================================================
# SESSION BUFFER (Stage 1: Bifurcated Memory System)
# =============================================================================
# Temporary buffer that stores raw text of user and agent turns
# for the current 5-turn cycle. Cleared after summarization.

_buffer = []  # In-memory buffer for current cycle

def _get_session_file():
    """
    Get or create the current session file.
    Creates a new file for each conversation session.
    Naming: convo_2026-02-06_11-30-45.txt
    """
    global _current_session_file
    
    if _current_session_file is None:
        # Create new session file with date and time
        os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        _current_session_file = os.path.join(LOG_DIR, f"convo_{timestamp}.txt")
        
        # Write session header
        with open(_current_session_file, "w", encoding="utf-8") as f:
            f.write(f"# Conversation Session Started: {datetime.now().isoformat()}\n")
            f.write("#" + "="*70 + "\n\n")
    
    return _current_session_file

def start_new_session():
    """
    Force start a new conversation session with a new file.
    Call this at program startup.
    """
    global _current_session_file
    _current_session_file = None
    # Pre-create the file
    _get_session_file()

def buffer_add(role, content):
    """
    Add a turn to the session buffer.
    role: 'user' or 'assistant'
    content: the message text
    """
    global _buffer
    timestamp = datetime.now().isoformat()
    _buffer.append({
        "timestamp": timestamp,
        "role": role,
        "content": content
    })

def buffer_get():
    """Get all items in the current buffer."""
    return _buffer.copy()

def buffer_clear():
    """Clear the buffer after summarization."""
    global _buffer
    _buffer = []

def buffer_to_raw_text():
    """
    Convert buffer to raw text format for summarizer input.
    Returns a formatted string of the conversation.
    """
    lines = []
    for item in _buffer:
        role_label = "USER" if item["role"] == "user" else "AI"
        lines.append(f"{role_label}: {item['content']}")
    return "\n".join(lines)

def buffer_save_to_file():
    """
    Persist buffer to disk as backup (optional, for recovery).
    Returns the file path.
    """
    os.makedirs(BUFFER_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(BUFFER_DIR, f"session_buffer_{timestamp}.txt")
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(buffer_to_raw_text())
    
    return filepath

def log_message(role, content, add_to_buffer=True):
    """
    Logs a conversation message to the current session file.
    Also adds to session buffer if add_to_buffer=True.
    
    role: 'user' or 'assistant'
    content: the message text
    add_to_buffer: whether to add to the temporary session buffer
    """
    # Get or create session file
    log_file = _get_session_file()
    
    # Timestamp: [16:37:45]
    time_str = datetime.now().strftime("%H:%M:%S")
    
    # Format: [16:37:45] user: hello
    log_line = f"[{time_str}] {role}: {content}\n"
    
    # Append to session file
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)
    
    # Also add to session buffer for bifurcated memory system
    if add_to_buffer:
        buffer_add(role, content)

def get_recent_history(hours=24, limit=10):
    """
    Retrieves recent conversation history from the current session file.
    Returns list of (timestamp, role, content) tuples.
    """
    history = []
    log_file = _get_session_file()
    
    if not os.path.exists(log_file):
        return history
    
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Parse last N lines (skip header lines starting with #)
    for line in lines[-limit:]:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Parse: [16:37:45] user: hello
        if line.startswith("[") and "]" in line:
            try:
                time_part = line[1:line.index("]")]
                rest = line[line.index("]")+2:]  # Skip "] "
                if ": " in rest:
                    role, content = rest.split(": ", 1)
                    history.append((time_part, role, content))
            except ValueError:
                continue
    
    return history

def get_current_session_file():
    """Get the path to the current session file."""
    return _get_session_file()
