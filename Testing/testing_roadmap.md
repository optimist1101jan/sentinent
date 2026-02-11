# Testing Roadmap — Layer-by-Layer

> Bottom-up approach: test the foundation first, then build upward.
> Derived from [HLD.md Section 12](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/HLD.md) (File Dependency Graph).
> 
>  **Low-value skipping:** Testing "simple getters" is a waste of time. That is  **Smart**.
>  **The "Sweet Spot" chart:** This is a real industry concept. Testing has diminishing returns.
>  
>  **At last generate HTML** coverage report so you can see which parts of your code are currently "unprotected"

---

## Dependency Layers

```
LAYER 4 — TOP (test LAST)
┌──────────────────────────────────────────┐
│  main.py — Orchestrator, CLI loop        │
│  Changes when you add features           │
└──────────────┬───────────────────────────┘
               │ depends on ↓
               │
LAYER 3 — PIPELINE (test THIRD)
┌──────────────────────────────────────────┐
│  packet_builder.py — Assembles XML       │
│  renderer_streaming.py — Calls API       │
│  summarizer_builder.py — Summarize+store │
└──────────────┬───────────────────────────┘
               │ depends on ↓
               │
LAYER 2 — CONTEXT (test SECOND)
┌──────────────────────────────────────────┐
│  memory_loader.py — Uses memory+semantic │
│  proximity_manager.py — Uses embeddings  │
│  dynamic_lore.py — Uses semantic_search  │
│  conversation.py — Reads/writes logs     │
└──────────────┬───────────────────────────┘
               │ depends on ↓
               │
               │
               │
               │
LAYER 1 — CORE (test FIRST) 🎯
┌──────────────────────────────────────────┐
│  renderer_base.py — clean/validate/parse │
│  temporal.py — time delta logic          │
│  memory.py — SQLite FTS5 operations      │
│  semantic_search.py — FAISS operations   │
│  model_config.py — constants             │
└──────────────────────────────────────────┘
  ↑ Zero project dependencies. Pure utilities.
```

**Rule:** If Layer 1 is broken → everything above is broken.
If Layer 1 is tested → you KNOW the foundation works.

---

## Testing Order — Checklist

### Layer 1 — Core (start here)

- [ ] **[renderer_base.py](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/pipeline/renderer_base.py)** — Pure functions, zero deps, easiest win (~6-8 tests)
  - [ ] [clean_response()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/pipeline/renderer_base.py#58-69) strips `[AI]:` prefixes
  - [ ] [clean_response()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/pipeline/renderer_base.py#58-69) strips punctuation artifacts
  - [ ] [validate()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/pipeline/renderer_base.py#71-82) rejects empty/short responses
  - [ ] [validate()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/pipeline/renderer_base.py#71-82) catches user impersonation
  - [ ] [parse_sections()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/pipeline/renderer_base.py#88-95) extracts XML tags correctly
  - [ ] [parse_sections()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/pipeline/renderer_base.py#88-95) handles missing tags
  - [ ] [build_gemini_payload()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/pipeline/renderer_base.py#97-143) produces correct structure
  - [ ] [load_api_key()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/pipeline/renderer_base.py#35-48) handles missing file

- [ ] **[temporal.py](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/agent/temporal.py)** — Only needs [json](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/agent/timestamps.json) + `datetime` (~4-5 tests)
  - [ ] [load_and_update()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/agent/temporal.py#13-48) calculates minutes/hours/days correctly
  - [ ] Handles missing [timestamps.json](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/agent/timestamps.json) (first run)
  - [ ] Handles corrupted [timestamps.json](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/agent/timestamps.json)
  - [ ] [get_time_block()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/agent/temporal.py#49-58) formats string correctly

- [ ] **[memory.py](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/agent/memory.py)** — Mock with in-memory SQLite (~5-6 tests)
  - [ ] [_init_db()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/agent/memory.py#13-26) creates FTS5 table
  - [ ] [add_episode()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/agent/memory.py#115-134) stores and returns rowid
  - [ ] [search()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/agent/memory.py#57-107) finds matching memories
  - [ ] [search()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/agent/memory.py#57-107) handles special characters / empty query
  - [ ] [wipe_memory()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/agent/memory.py#108-114) clears everything

### Layer 2 — Context (after Layer 1 passes)

- [ ] **[conversation.py](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/agent/conversation.py)** — Mock with temp directory (~4-5 tests)
  - [ ] `log_message()` writes to correct file
  - [ ] `get_recent_history()` returns correct count
  - [ ] `buffer_clear()` clears buffer
  - [ ] `buffer_to_raw_text()` formats correctly

- [ ] **`memory_loader.py`** — Mock Layer 1 deps (~3 tests)
  - [ ] Intent detection ("do you remember" → triggers search)
  - [ ] No intent → no memory section
  - [ ] Returns formatted `<memory_bank>` block

### Layer 3 — Pipeline (after Layer 2 passes)

- [ ] **[packet_builder.py](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/pipeline/packet_builder.py)** — Integration test (~3-4 tests)
  - [ ] [build()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/pipeline/packet_builder.py#26-114) produces valid XML with all sections
  - [ ] Proximity block appears on first turn
  - [ ] Memory block appears only on memory intent

- [ ] **[main.py](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/main.py)** — [is_valid_response()](file:///c:/Users/PC/Desktop/New%20folder/Persistent-AI-Systems-/main.py#13-31) (~3 tests)
  - [ ] Rejects empty string
  - [ ] Rejects fallback message
  - [ ] Accepts valid response

### Layer 4 — End-to-End (after everything passes)

- [ ] **Pipeline integration** — Mock the Gemini API (~2-3 tests)
  - [ ] Full chain: input → build → render → validate → commit
  - [ ] Invalid response → discard (nothing logged)
  - [ ] 5-turn cycle triggers summarizer

---

## Total: ~25-30 tests → ~80% critical path coverage

```
Layer 1:  ~15 tests   (foundation)
Layer 2:  ~7 tests    (context glue)
Layer 3:  ~6 tests    (assembly)
Layer 4:  ~3 tests    (full pipeline)
─────────────────────
Total:    ~31 tests
```
