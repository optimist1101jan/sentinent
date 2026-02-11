# 📊 Logger System — Priority Dashboard

> A Markdown table-based logging system for the Persistent Character Agent.  
> Logs are written to `data/system_logs/Log_Files.md` in real-time and can be previewed in VS Code's Markdown viewer.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Table Format](#table-format)
- [Module Icon Map](#module-icon-map)
- [Severity Levels](#severity-levels)
- [File Rotation](#file-rotation)
- [Session Lifecycle](#session-lifecycle)
- [Instrumented Files](#instrumented-files)
- [Safety Guards](#safety-guards)
- [Usage](#usage)
- [Configuration](#configuration)
- [Design Decisions](#design-decisions)

---

## Overview

The logging system outputs a **Markdown table** to `data/system_logs/Log_Files.md` that acts as a real-time Priority Dashboard. Every log entry becomes a table row with severity, module icon, timestamp, source file, and message — making it trivial to scan for errors visualy or sort/filter in any Markdown viewer.

**Key Properties:**
- 🟢 **Additive** — All existing `print()` statements remain untouched
- 🔒 **Independent** — Completely separate from the test framework
- 📁 **Centralized** — Single config in `logger_config.py`, used by all modules
- 🔄 **Self-healing** — Rotating files with auto-generated table headers

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    logger_config.py                      │
│                                                          │
│  ┌──────────────────┐    ┌─────────────────────────────┐ │
│  │  TableFormatter  │    │  TableRotatingHandler       │ │
│  │                  │    │                             │ │
│  │  • Severity map  │    │  • 5MB max per file         │ │
│  │  • Module icons  │    │  • 3 backup files           │ │
│  │  • 12hr AM/PM    │    │  • Auto table header on     │ │
│  │  • Date column   │    │    new/rotated files        │ │
│  └──────────────────┘    └─────────────────────────────┘ │
│                                                          │
│  ┌──────────────────┐    ┌─────────────────────────────┐ │
│  │ ConsoleFormatter │    │  Session Management         │ │
│  │                  │    │                             │ │
│  │  • WARNING+ only │    │  • log_session_start()      │ │
│  │  • Emoji prefix  │    │  • log_session_end()        │ │
│  │  • Minimal noise │    │  • atexit shutdown hook     │ │
│  │                  │    │  • Duplicate guard flag     │ │
│  └──────────────────┘    └─────────────────────────────┘ │
│                                                          │
│  get_logger(__name__) → SentientLog.<module> namespace   │
└──────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
  ┌─────────────┐          ┌──────────────────────┐
  │   Console   │          │  Log_Files.md        │
  │  (stderr)   │          │  Log_Files.md.1      │
  │             │          │  Log_Files.md.2      │
  │  WARNING+   │          │  Log_Files.md.3      │
  │  only       │          │  (rotated backups)   │
  └─────────────┘          └──────────────────────┘
```

---

## Table Format

Every log entry is a single Markdown table row:

```markdown
| Priority | Status | Date | Timestamp | Module | Message |
| :--- | :--- | :--- | :--- | :--- | :--- |
| MEDIUM | 🟢 | `2026-02-11` | `03:15:43.846 PM` | 🪄 `renderer_base.py` | API key loaded successfully |
| HIGH | 🔴 | `2026-02-11` | `03:16:10.122 PM` | 🪄 `renderer_streaming.py` | HTTP error - Status: 429 |
```

**Rendered Preview:**

| Priority | Status | Date | Timestamp | Module | Message |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **---** | **🤖** | `2026-02-11` | **`03:15:43 PM`** | **SESSION** | **🤖 Sentient Activity Log — Session Start** |
| MEDIUM | 🟢 | `2026-02-11` | `03:15:43.846 PM` | 🪄 `renderer_base.py` | API key loaded successfully |
| MEDIUM | 🟢 | `2026-02-11` | `03:19:45.657 PM` | ⚙️ `main.py` | Request received - HOLD: "hi" |
| LOW | 🔵 | `2026-02-11` | `03:19:45.738 PM` | 🧠 `memory_loader.py` | Memory intent detected |
| HIGH | 🔴 | `2026-02-11` | `03:20:10.122 PM` | 🪄 `renderer_streaming.py` | HTTP error - Status: 429 |
| **---** | **🏁** | `2026-02-11` | **`03:20:39 PM`** | **SESSION** | **Session closed** |

---

## Module Icon Map

Each source file is mapped to a category icon for instant visual identification:

| Icon | Category | Files |
| :---: | :--- | :--- |
| 🪄 | **LLM / API** | `renderer.py`, `renderer_streaming.py`, `renderer_base.py`, `model_config.py`, `summarizer_builder.py` |
| 🧠 | **Memory** | `memory.py`, `memory_loader.py`, `semantic_search.py` |
| ⚙️ | **System** | `main.py`, `logger_config.py`, `packet_builder.py`, `temporal.py`, `conversation.py` |
| 🛡️ | **Safety** | `proximity_manager.py` |

> Files not in the map default to ⚙️ System.

---

## Severity Levels

Log levels map to a 3-tier priority system:

| Python Level | Priority | Status Icon | Use Case |
| :--- | :--- | :---: | :--- |
| `DEBUG` | LOW | 🔵 | Breadcrumbs — flow tracing, search results, packet sizes |
| `INFO` | MEDIUM | 🟢 | Key events — system init, API calls, commits, memory hits |
| `WARNING` | MEDIUM | 🟡 | Degraded state — missing model, fallback triggered |
| `ERROR` | HIGH | 🔴 | Failures — API errors, timeouts, index failures |
| `CRITICAL` | HIGH | 💀 | Fatal — unrecoverable errors |

---

## File Rotation

```
data/system_logs/
├── Log_Files.md      ← Current (actively writing)
├── Log_Files.md.1    ← Previous session backup
├── Log_Files.md.2    ← Older backup
└── Log_Files.md.3    ← Oldest (deleted when 4th would be created)
```

| Setting | Value |
| :--- | :--- |
| Max file size | 5 MB |
| Backup count | 3 |
| Total log capacity | ~20 MB (4 × 5 MB) |
| Encoding | UTF-8 |

### Header Guard

The `TableRotatingHandler` overrides `_open()` to detect empty files (new or just-rotated) and automatically writes the Markdown table header:

```python
def _open(self):
    stream = super()._open()
    stream.seek(0, 2)  # Seek to end
    if stream.tell() == 0:  # File is empty
        stream.write(TABLE_HEADER)
        stream.flush()
    return stream
```

This ensures every rotated log file starts with a valid table header — the table never breaks.

---

## Session Lifecycle

```
Program Start
    │
    ├─ log_session_start()  →  | --- | 🤖 | ... | SESSION | Session Start |
    │
    ├─ [normal logging rows...]
    │
    ├─ log_session_end()    →  | --- | 🏁 | ... | SESSION | Session closed |
    │
    └─ atexit hook fires    →  (guarded: skips if already called)
```

### Duplicate Guard

`log_session_end()` uses a `_session_ended` flag to prevent double writes:

```python
_session_ended = False

def log_session_end():
    global _session_ended
    if _session_ended:
        return          # ← atexit fires but skips
    _session_ended = True
    # ... write session end row
```

**Why:** `main.py` calls `log_session_end()` explicitly on exit, AND `atexit` fires it again. The guard ensures only one `🏁 Session closed` row appears.

### Import Order

`log_session_start()` is called at the **top** of `main.py`, before any other imports that trigger logging:

```python
# main.py (top of file)
from logger_config import get_logger, log_session_start, log_session_end
log_session_start()   # ← BEFORE renderer_base imports and logs API key
logger = get_logger(__name__)

from pipeline.renderer_base import ...  # This logs "API key loaded"
```

This guarantees the `🤖 Session Start` row always appears first in the table.

---

## Instrumented Files

Every source file has been instrumented with `logger.*` calls at key events:

| File | Logger Lines | Events Logged |
| :--- | :---: | :--- |
| `main.py` | 12 | Session lifecycle, request/response, COMMIT/DISCARD, summarizer trigger, errors |
| `renderer_streaming.py` | 5 | API call start, HTTP errors, parse failures, empty responses |
| `renderer.py` | 9 | Retries, cache hits, validation failures, HTTP errors |
| `summarizer_builder.py` | 8 | Summarization start/result, episodic/semantic index success/failure |
| `renderer_base.py` | 3 | API key load success/failure |
| `memory_loader.py` | 4 | Intent detection, memory retrieval results |
| `semantic_search.py` | 6 | Index build, model load, search execution, chunk addition |
| `memory.py` | 4 | Episode add, FTS5 search results, memory wipe |
| `proximity_manager.py` | 3 | Model load, state changes |
| `model_config.py` | 2 | API key failures, generate_response errors |

> **Total: ~56 logger lines across 10 files. Zero `print()` statements were modified.**

---

## Safety Guards

### No-Noise Guard (Semantic Search)

When the embedding model (`nomic-embed-text-v1.5.Q8_0.gguf`) is missing:

- `_embed()` returns `None` instead of random vectors
- `search()` returns `[]` (empty list)
- `build_index()` skips building, clears chunk list
- `add_chunk_to_index()` returns `False`

**Result:** No garbage data enters the packet prompt. The `<memory_bank>` tag stays clean.

---

## Usage

### Basic

```python
from logger_config import get_logger

logger = get_logger(__name__)

logger.debug("Packet built - 1240 chars")        # LOW  🔵
logger.info("System initialized")                 # MEDIUM 🟢
logger.warning("Model not found")                 # MEDIUM 🟡
logger.error("API timeout - Status: 429")          # HIGH 🔴
```

### With Exception Traceback

```python
try:
    response = requests.post(url, data=payload)
except Exception as e:
    logger.error(f"Request failed: {e}", exc_info=True)
    # → Appends collapsed traceback to the Message column
```

### Session Control

```python
from logger_config import log_session_start, log_session_end

log_session_start()   # Writes 🤖 Session Start row
# ... application runs ...
log_session_end()     # Writes 🏁 Session closed row
```

---

## Configuration

All settings live in `logger_config.py`:

| Setting | Location | Default |
| :--- | :--- | :--- |
| Log file path | `LOG_FILE` | `data/system_logs/Log_Files.md` |
| Max file size | `TableRotatingHandler(maxBytes=...)` | 5 MB |
| Backup count | `TableRotatingHandler(backupCount=...)` | 3 |
| File log level | `file_handler.setLevel(...)` | `DEBUG` (all levels) |
| Console log level | `console_handler.setLevel(...)` | `WARNING` (errors only) |
| Time format | `TableFormatter.format()` | 12-hour AM/PM with ms |
| Module icons | `MODULE_ICONS` dict | See Module Icon Map |

---

## Design Decisions

| Decision | Rationale |
| :--- | :--- |
| **Table format over block format** | Sortable, filterable, scannable at a glance in any Markdown viewer |
| **Additive logging** | Zero risk of breaking existing behavior — `print()` stays, `logger.*` adds alongside |
| **Separated from tests** | Logger is a production tool, not a testing concern |
| **Module-level icons** | Instant visual grouping without reading filenames |
| **3-tier severity** | Maps cleanly to action priority: ignore (LOW), note (MEDIUM), fix now (HIGH) |
| **`atexit` shutdown hook** | Ensures session end is always logged, even on `Ctrl+C` |
| **Header guard on rotation** | Prevents broken Markdown tables when log files rotate |
| **No-noise guard** | Random vectors from missing models don't pollute the LLM prompt |
| **`SentientLog` namespace** | All loggers live under one root — easy to globally configure or silence |
| **12-hour AM/PM format** | Human-friendly timestamps for manual log review |
