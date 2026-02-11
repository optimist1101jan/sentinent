# 📊 v0.2.0: Logger Integrated

**"Priority Dashboard" — Real-Time System Visibility**

This release introduces a production-grade, standalone logging infrastructure designed for debugging complex agent behaviors without cluttering the console or interfering with tests.

![Logger Dashboard Preview](https://github.com/user-attachments/assets/placeholder-image-id)

## 🚀 Key Features

### 1. The Priority Dashboard
- **Markdown Table Format**: Logs are written as a structured table to `data/system_logs/Log_Files.md`.
- **Visual Scanning**: Instant readability with module icons (🪄, 🧠, ⚙️, 🛡️) and status indicators.
- **Severity Levels**:
  - 🔵 **LOW (DEBUG)**: Breadcrumbs, flow tracing.
  - 🟢 **MEDIUM (INFO/WARN)**: Key events, successful operations.
  - 🔴 **HIGH (ERROR)**: Failures, API timeouts, logic breaks.

### 2. Full System Instrumentation
Added ~56 logger calls across 10 core files, covering the entire agent lifecycle:
- **Session**: Start/End markers, turn counters.
- **Memory**: Intent detection, FTS5/FAISS search results.
- **API**: Request/Response tracking, token usage (approx), retries.
- **Safety**: Proximity state changes, model loading failures.

### 3. Noise Guard 🛡️
- **Smart Fallback**: If the local embedding model (`nomic-embed-text`) is missing, the system now gracefully skips semantic search instead of generating random noise vectors.
- **Clean Prompts**: Ensures no garbage data enters the LLM context window during degraded states.

### 4. Robust Architecture
- **Additive Logging**: Zero changes to existing `print()` statements — 100% backward compatible.
- **Self-Healing**: Automatic file rotation (5MB limit, 3 backups) with auto-regenerated table headers.
- **Crash-Proof**: `atexit` hooks ensure "Session Closed" markers are written even on `Ctrl+C`.

---

## 🛠️ Usage

The log file is located at:
`data/system_logs/Log_Files.md`

Open it in VS Code and use the **Markdown Preview** (`Ctrl+Shift+V`) to see the live dashboard.

## 📦 Technical Details

- **New Module**: `logger_config.py` (Centralized configuration)
- **New Doc**: `Logger_System.md` (Full system architecture)
- **Ignored**: `Testing/` directory removed from tracking to keep the repo clean.
