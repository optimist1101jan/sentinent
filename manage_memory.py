"""
Memory Management Utility - manage_memory.py

Stage 4: Manual Memory Cleanup Tool
Allows safe deletion of memories while maintaining index alignment.

Usage:
    python manage_memory.py list       # View all memories
    python manage_memory.py delete <id> # Delete specific memory
    python manage_memory.py stats      # Show memory statistics
    python manage_memory.py rebuild    # Force rebuild FAISS index
    python manage_memory.py clear      # Clear all memories (with confirmation)
"""

import os
import sys
import json
import sqlite3

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.join(SCRIPT_DIR, "agent")
DB_PATH = os.path.join(AGENT_DIR, "brain.db")
CHUNKS_PATH = os.path.join(AGENT_DIR, "semantic_chunks.json")
INDEX_PATH = os.path.join(AGENT_DIR, "semantic.index")


def get_db_connection():
    """Get SQLite connection to brain.db."""
    if not os.path.exists(DB_PATH):
        print(f"[Error] Database not found at {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def view_memories():
    """View all memories in the database."""
    print("=" * 70)
    print("MEMORY VIEWER")
    print("=" * 70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT rowid, content, filename, timestamp FROM episodes ORDER BY rowid")
    rows = cursor.fetchall()
    
    if not rows:
        print("\nNo memories found in database.")
        conn.close()
        return
    
    print(f"\nTotal memories: {len(rows)}\n")
    print("-" * 70)
    
    for rowid, content, filename, timestamp in rows:
        preview = content[:50] + "..." if len(content) > 50 else content
        preview = preview.replace("\n", " ")
        
        print(f"ID: {rowid}")
        print(f"Source: {filename}")
        print(f"Time: {timestamp}")
        print(f"Text: {preview}")
        print("-" * 70)
    
    conn.close()
    print(f"\nUse 'python manage_memory.py delete <id>' to remove a memory.\n")


def delete_memory(target_id: int):
    """Delete a memory from both brain.db and semantic_chunks.json."""
    print("=" * 70)
    print("MEMORY DELETION")
    print("=" * 70)
    
    print(f"\n[Step 1/3] Deleting from brain.db (ID: {target_id})...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT content, filename FROM episodes WHERE rowid = ?", (target_id,))
    row = cursor.fetchone()
    
    if not row:
        print(f"[Error] Memory with ID {target_id} not found in brain.db")
        conn.close()
        return
    
    content, filename = row
    preview = content[:50] + "..." if len(content) > 50 else content
    print(f"Found: {preview}")
    
    confirm = input(f"\nAre you sure you want to delete this memory? (yes/no): ")
    if confirm.lower() not in ["yes", "y"]:
        print("Deletion cancelled.")
        conn.close()
        return
    
    cursor.execute("DELETE FROM episodes WHERE rowid = ?", (target_id,))
    conn.commit()
    deleted_count = cursor.rowcount
    conn.close()
    
    if deleted_count == 0:
        print(f"[Error] Failed to delete memory with ID {target_id}")
        return
    
    print(f"[OK] Deleted from brain.db")
    
    print(f"\n[Step 2/3] Removing from semantic_chunks.json...")
    
    if not os.path.exists(CHUNKS_PATH):
        print(f"[Warning] semantic_chunks.json not found, skipping...")
    else:
        with open(CHUNKS_PATH, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        original_count = len(chunks)
        new_chunks = []
        removed = False
        
        for source, text in chunks:
            if text == content and not removed:
                print(f"[OK] Found matching chunk in semantic memory")
                removed = True
                continue
            new_chunks.append((source, text))
        
        if removed:
            with open(CHUNKS_PATH, 'w', encoding='utf-8') as f:
                json.dump(new_chunks, f, ensure_ascii=False, indent=2)
            print(f"[OK] Removed from semantic_chunks.json ({original_count} → {len(new_chunks)})")
        else:
            print(f"[Warning] No matching chunk found in semantic_chunks.json")
    
    print(f"\n[Step 3/3] Rebuilding FAISS index for alignment...")
    
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from agent.semantic_search import rebuild_index
        rebuild_index()
        print("[OK] FAISS index rebuilt successfully")
    except Exception as e:
        print(f"[Error] Failed to rebuild index: {e}")
    
    print("\n" + "=" * 70)
    print(f"Memory {target_id} successfully pruned from system.")
    print("=" * 70)


def rebuild_memory_index():
    """Force rebuild the FAISS index from scratch."""
    print("=" * 70)
    print("MEMORY INDEX REBUILD")
    print("=" * 70)
    
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from agent.semantic_search import rebuild_index
        print("\nRebuilding index from all sources (lore + episodes)...")
        rebuild_index()
        print("\n[OK] Index rebuild complete!")
    except Exception as e:
        print(f"\n[Error] Rebuild failed: {e}")


def clear_all_memories():
    """Clear all memories from the database."""
    print("=" * 70)
    print("CLEAR ALL MEMORIES")
    print("=" * 70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM episodes")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("\nNo memories to clear.")
        conn.close()
        return
    
    print(f"\nThis will delete ALL {count} memories from the database.")
    confirm = input("Are you ABSOLUTELY sure? Type 'DELETE ALL' to confirm: ")
    
    if confirm != "DELETE ALL":
        print("Operation cancelled.")
        conn.close()
        return
    
    cursor.execute("DELETE FROM episodes")
    conn.commit()
    conn.close()
    
    print(f"[OK] Deleted {count} memories from brain.db")
    
    # Clear semantic chunks
    if os.path.exists(CHUNKS_PATH):
        with open(CHUNKS_PATH, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("[OK] Cleared semantic_chunks.json")
    
    # Rebuild index
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from agent.semantic_search import rebuild_index
        rebuild_index()
        print("[OK] Rebuilt empty index")
    except Exception as e:
        print(f"[Warning] Index rebuild failed: {e}")
    
    print("\n" + "=" * 70)
    print("All memories cleared.")
    print("=" * 70)


def show_stats():
    """Show memory system statistics."""
    print("=" * 70)
    print("MEMORY STATISTICS")
    print("=" * 70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM episodes")
    episodic_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT filename, COUNT(*) as count FROM episodes GROUP BY filename")
    source_breakdown = cursor.fetchall()
    conn.close()
    
    print(f"\n[Episodic Memory - brain.db]")
    print(f"  Total entries: {episodic_count}")
    if source_breakdown:
        print(f"  By source:")
        for source, count in source_breakdown:
            print(f"    - {source}: {count}")
    
    print(f"\n[Semantic Memory - FAISS]")
    if os.path.exists(CHUNKS_PATH):
        with open(CHUNKS_PATH, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        print(f"  Indexed chunks: {len(chunks)}")
    else:
        print(f"  semantic_chunks.json: NOT FOUND")
    
    if os.path.exists(INDEX_PATH):
        size_kb = os.path.getsize(INDEX_PATH) / 1024
        print(f"  FAISS index size: {size_kb:.1f} KB")
    else:
        print(f"  semantic.index: NOT FOUND")
    
    print("\n" + "=" * 70)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nCommands:")
        print("  list              - View all memories")
        print("  delete <id>       - Delete memory by ID")
        print("  stats             - Show memory statistics")
        print("  rebuild           - Force rebuild FAISS index")
        print("  clear             - Clear all memories (with confirmation)")
        print("\nExample:")
        print("  python manage_memory.py list")
        print("  python manage_memory.py delete 42")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        view_memories()
    elif command == "delete":
        if len(sys.argv) < 3:
            print("[Error] Please specify an ID to delete")
            print("Usage: python manage_memory.py delete <id>")
            sys.exit(1)
        try:
            target_id = int(sys.argv[2])
            delete_memory(target_id)
        except ValueError:
            print("[Error] ID must be a number")
            sys.exit(1)
    elif command == "stats":
        show_stats()
    elif command == "rebuild":
        rebuild_memory_index()
    elif command == "clear":
        clear_all_memories()
    else:
        print(f"[Error] Unknown command: {command}")
        print("Use: list, delete, stats, rebuild, or clear")
        sys.exit(1)


if __name__ == "__main__":
    main()
