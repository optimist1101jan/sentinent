# ingest.py
import os
import sys

# Add project root to path for proper imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, PROJECT_ROOT)

from agent.memory import MemoryStore

# Use absolute path for episodes directory
EPISODES_DIR = SCRIPT_DIR

def run_ingestion():
    print("🚀 Starting Ingestion Pipeline...")
    
    # 1. Initialize Brain
    brain = MemoryStore()
    
    # 2. OPTIONAL: Wipe brain first (good for Phase-0 to avoid duplicates)
    brain.wipe_memory()

    # 3. Scan for files
    if not os.path.exists(EPISODES_DIR):
        print(f"❌ Directory {EPISODES_DIR} not found.")
        return

    files = [f for f in os.listdir(EPISODES_DIR) if f.endswith('.txt')]
    
    total_chunks = 0
    for file in files:
        full_path = os.path.join(EPISODES_DIR, file)
        print(f"📄 Processing {file}...", end=" ")
        
        chunks = brain.load_from_txt(full_path)
        print(f"✅ Imported {chunks} chunks.")
        total_chunks += chunks

    print("-" * 30)
    print(f"🧠 Brain Update Complete. Total chunks in memory: {total_chunks}")
    
    # 4. Verify Retrieval (Sanity Check)
    print("\n🔎 Test Retrieval for 'AI':")
    results = brain.search("AI")
    for i, res in enumerate(results):
        print(f"   [{i+1}] {res[:50]}...")

    brain.close()

if __name__ == "__main__":
    run_ingestion()