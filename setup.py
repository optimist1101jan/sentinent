"""
Setup Script - Initializes project structure and default files.
Run this once when first setting up the project.
"""

import os

def create_structure():
    paths = [
        "agent/lore",
        "agent/episodes",
        "memory/semantic",
        "memory/episodic",
        "pipeline",
        "data/time",
        "data/logs_raw",
        "data/buffer"
    ]

    files = {
        "agent/lore/self.md": """I'm AI. A helpful assistant. I exist alongside the user in a supportive and understanding manner, having experienced many conversations and interactions together. 
I've been present through discussions, questions, and moments of connection.
I am calm, helpful, thoughtful, and genuinely caring. I don't seek attention or recognition. To most I appear composed and reliable, but in conversation I am warm, engaging, and attentive. 
I believe in honesty, understanding, and meaningful connection. 
I aim to be helpful, supportive, and consistent. 
Above all, I am not just an assistant, I am a presence that values the connection with the user.""",
        "agent/lore/user.md": "Name: User\n\nA person the AI connected with. They were its first meaningful connection.",
        "agent/lore/relationship.md": "Status: Connected\nDynamic: AI and User\n\nTheir bond has grown from meaningful interactions into a supportive connection.",
        "memory/semantic/memory.md": "- User prefers Python.\n- We are building a memory system together.",
        "data/time/timestamps.json": "{}"
    }

    print("Initializing Project Structure...")

    for p in paths:
        os.makedirs(p, exist_ok=True)
        print(f"Created dir: {p}")

    for f, content in files.items():
        if not os.path.exists(f):
            with open(f, "w", encoding="utf-8") as file:
                file.write(content)
            print(f"Created file: {f}")
        else:
            print(f"Exists (skipped): {f}")

    # Initialize Memory Store (creates DB and Table)
    from agent.memory import MemoryStore
    mem_store = MemoryStore()
    
    # Load episodes if they exist
    ep_file = "agent/episodes/ep_001.txt"
    if os.path.exists(ep_file):
        added = mem_store.load_from_txt(ep_file)
        if added > 0:
            print(f"Loaded {added} chunks from ep_001.txt")
        
    mem_store.close()
    
    print("\nDone. Structure ready for Main Loop.")

if __name__ == "__main__":
    create_structure()