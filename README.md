# 🧠 Persistent Character Agent

A persistent conversational AI agent with **long-term memory**, **dynamic identity**, **proximity awareness**, and **real-time streaming responses** — powered by **Google Gemini API**.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Google%20Gemini-API-4285F4?logo=google&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-Vector%20Search-orange)
![SQLite](https://img.shields.io/badge/SQLite-FTS5-003B57?logo=sqlite&logoColor=white)
![Streaming](https://img.shields.io/badge/Real--Time-Streaming-FF69B4?logo=statuspage&logoColor=white)
![Bifurcated Memory](https://img.shields.io/badge/Memory-Bifurcated%20System-9C27B0?logo=brainstore&logoColor=white)
![Summarization](https://img.shields.io/badge/Auto--Summarization-Recursive-4CAF50?logo=element&logoColor=white)
![Dynamic Lore](https://img.shields.io/badge/Dynamic%20Lore-Semantic%20Retrieval-FF9800?logo=knowledge-base&logoColor=white)
![Proximity](https://img.shields.io/badge/Proximity-Nomic%20Embeddings-00A6ED?logo=radar&logoColor=white)
![Temporal](https://img.shields.io/badge/Temporal%20Awareness-Context%20Drift-795548?logo=clockify&logoColor=white)
![Traffic Control](https://img.shields.io/badge/Traffic%20Control-Hold--Wait--Commit-D32F2F?logo=traefik&logoColor=white)
![Caching](https://img.shields.io/badge/Response%20Caching-Hash--Based-607D8B?logo=files&logoColor=white)

#### 🔬🛠️✅ Current Status: In the Testing and Stabilization Phase...
---

## ✨ Features

- **🔄 Real-Time Streaming** — Typewriter-style character-by-character response display via Gemini streaming API
- **🧠 Bifurcated Memory System** — Dual-layer memory with episodic (SQLite FTS5) and semantic (FAISS) recall
- **📝 Auto-Summarization** — Every 5 turns are compressed into a single memory sentence and indexed into long-term storage
- **🎭 Dynamic Lore Retrieval** — Personality and knowledge chunks retrieved via semantic search, not static injection
- **📍 Proximity Detection** — Nomic embedding-based detection of physical/remote/transitional presence states
- **🕐 Temporal Awareness** — Tracks time between conversations and adjusts context accordingly
- **🛡️ Traffic Control** — Hold-Wait-Commit pattern ensures only valid responses are logged
- **💾 Response Caching** — Deduplicates API calls with local hash-based cache
- **🔧 Memory Management CLI** — List, delete, clear, and rebuild memory from the command line

---

## 🏗️ Architecture

```
project/
├── main.py                     # Entry point — CLI loop, streaming, 5-turn cycles
├── model_config.py             # LLM configuration (model, API, generation params)
├── setup.py                    # Initialize project structure and default files
├── manage_memory.py            # Memory management CLI tool
├── check_models.py             # List available models for your API key
├── requirements.txt
│
├── agent/                      # State & Retrieval Layer
│   ├── temporal.py             # Time delta calculation
│   ├── memory.py               # SQLite FTS5 episodic storage
│   ├── semantic_search.py      # FAISS vector search (nomic-embed-text)
│   ├── conversation.py         # Session logging + buffer management
│   ├── dynamic_lore.py         # Semantic lore retrieval
│   ├── lore/                   # Static personality files
│   │   ├── self.md             # AI identity
│   │   ├── user.md             # User profile
│   │   └── relationship.md    # Connection definition
│   └── episodes/               # Raw memory source files
│
├── pipeline/                   # Prompt Construction & Rendering
│   ├── packet_builder.py       # XML-tagged prompt assembly
│   ├── renderer.py             # Gemini API (non-streaming, cached)
│   └── summarizer_builder.py   # 5-turn summarization pipeline
│
├── streaming/                  # Real-Time Response
│   └── renderer_streaming.py   # Streaming with typewriter effect
│
├── proximity/                  # Presence Detection
│   └── proximity_manager.py    # Nomic-based proximity state engine
│
├── memory/                     # Memory Intent & Retrieval
│   └── memory_loader.py        # Intent detection + multi-source fetching
│
├── tools/                      # Utilities
│   └── index_lore.py           # Rebuild lore index
│
└── data/
    ├── nomic-embed-text-v1.5.Q8_0.gguf  # Local embedding model
    └── logs_raw/               # Session conversation logs
```

---

## 🔁 Data Flow

```
User Input → HOLD (temporary, not logged)
     ↓
Build Packet (XML-tagged prompt)
  ├── Dynamic Lore     → Semantic search over personality chunks
  ├── Proximity State  → Inject if changed (embedding similarity)
  ├── Memory Bank      → Fetch if memory intent detected
  └── Chat History     → Last 6 turns
     ↓
Stream to Gemini API (gemma-3-12b-it)
     ↓
Typewriter Display → Clean [AI]: prefix → Validate
     ↓
Valid?  → COMMIT both messages to log + buffer
Invalid? → DISCARD (clean retry, no history pollution)
     ↓
Turn == 5? → Summarize → Index to brain.db + FAISS → Reset buffer
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [Google AI Studio API Key](https://aistudio.google.com/apikey) (free tier supports Gemma models)
- ~200MB disk space (for the Nomic embedding model)

### Installation

```bash
# Clone the repository
git clone https://github.com/optimist1101jan/Persistent-AI-Systems-.git

# Navigate to the project directory
cd Persistent-AI-Systems-

# Install dependencies
pip install -r requirements.txt

# Add your API key (Creates API_KEY.txt)
echo "API_KEY=your_gemini_api_key_here" > API_KEY.txt

# Initialize database and project structure
python setup.py

# Start the agent
python main.py
```

### Embedding Model Setup

Download the [nomic-embed-text-v1.5 GGUF](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF) model and place it in `data/`:

```bash
# Place the file at:
data/nomic-embed-text-v1.5.Q8_0.gguf
```

> **Note:** The agent works without the embedding model (using fallback), but semantic search and proximity detection require it.

---

## ⚙️ Configuration

All model settings are in `model_config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MODEL` | `gemma-3-12b-it` | Gemini/Gemma model to use |
| `TEMPERATURE` | `0.7` | Response creativity |
| `MAX_OUTPUT_TOKENS` | `1000` | Max response length |
| `TIMEOUT` | `60s` | API request timeout |
| `MAX_RETRIES` | `3` | Retry attempts on failure |

### Available Models

```
Free Tier (Gemma):                    Paid Tier (Gemini):
  gemma-3-1b-it   (fastest)            gemini-2.0-flash
  gemma-3-4b-it   (balanced)           gemini-2.0-flash-lite
  gemma-3-12b-it  (recommended)        gemini-2.5-flash
  gemma-3-27b-it  (best quality)       gemini-2.5-pro
```

Run `python check_models.py` to see all models available for your API key.

---

## 🧠 Memory System

The agent uses a **3-stage memory pipeline**:

### Stage 1 — Session Buffer
Raw conversation turns held in-memory for the current 5-turn cycle.

### Stage 2 — Summarization
After 5 turns, the buffer is sent to Gemini for compression into a single factual sentence.

### Stage 3 — Long-Term Indexing
The compressed memory is simultaneously indexed into:
- **Episodic Store** (SQLite FTS5) — keyword searchable
- **Semantic Index** (FAISS) — embedding-based similarity search

### Memory Retrieval
When the user asks a memory-related question (e.g., *"do you remember..."*), the system:
1. Detects memory intent via keyword patterns
2. Searches both episodic and semantic stores
3. Injects relevant memories into the prompt

---

## 🛠️ Memory Management

```bash
python manage_memory.py list            # View all stored memories
python manage_memory.py delete <id>     # Delete a specific memory
python manage_memory.py stats           # Show memory statistics
python manage_memory.py rebuild         # Rebuild FAISS index
python manage_memory.py clear           # Clear all memories
```

---

## 📍 Proximity System

The agent detects **physical presence context** using embedding similarity:

| State | Description | Example Input |
|-------|-------------|---------------|
| `PHYSICAL` | User is present, face-to-face | *"sits next to you"* |
| `REMOTE` | Chatting remotely | *"texting from work"* |
| `TRANSITION_TOWARD` | User arriving | *"walks over to you"* |
| `TRANSITION_AWAY` | User leaving | *"I need to go now"* |

Proximity context is only injected when the state **changes** or on the **first turn**, saving tokens.

---

## 📋 Tech Stack

| Component | Technology |
|-----------|-----------|
| **LLM** | Google Gemini API (Gemma 3 12B) |
| **Embeddings** | nomic-embed-text-v1.5 (GGUF, 768-dim) |
| **Vector Search** | FAISS (IndexFlatIP, cosine similarity) |
| **Episodic Memory** | SQLite FTS5 |
| **Embedding Runtime** | llama-cpp-python |
| **Streaming** | Gemini streamGenerateContent API |
| **Language** | Python 3.10+ |

---

## 🔒 Security Notes

- **Never commit `API_KEY.txt`** — add it to `.gitignore`
- The API key is loaded at runtime from a local file
- No external data is stored beyond local cache and logs

---

## 📄 License

This project is for educational and personal use. See individual dependency licenses for third-party components.
