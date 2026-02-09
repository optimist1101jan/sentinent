"""
Lore Indexer - tools/index_lore.py

Chunks lore files into semantic pieces and adds them to the main semantic index.
Run this script whenever lore files are updated.

Usage:
    python tools/index_lore.py

Output:
    - Updates agent/semantic_chunks.json with new lore chunks
    - Rebuilds agent/semantic.index (FAISS)
"""

import os
import sys

# Get project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BASE_DIR)

from agent.semantic_search import SemanticSearch


# Paths
LORE_DIR = os.path.join(BASE_DIR, "agent", "lore")


def chunk_lore_file(filepath: str, source_name: str) -> list:
    """
    Split a lore file into semantic chunks.
    
    Strategy:
    1. Split by paragraphs (double newlines)
    2. For long paragraphs (>250 chars), split into 2-sentence chunks
    
    Args:
        filepath: Path to the .md file
        source_name: Identifier like "lore/self", "lore/relationship"
        
    Returns:
        List of (source, text) tuples
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read().strip()
    
    if not text:
        return []
    
    # Split by double newlines (paragraphs)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    chunks = []
    for para in paragraphs:
        # Short paragraph: keep as-is
        if len(para) <= 250:
            chunks.append((source_name, para))
        else:
            # Long paragraph: split by sentences with 1-sentence overlap
            sentences = [s.strip() for s in para.split('. ') if s.strip()]
            
            if len(sentences) == 1:
                chunks.append((source_name, sentences[0]))
            else:
                # Create overlapping chunks of 2 sentences
                for i in range(0, len(sentences) - 1, 1):
                    chunk_text = sentences[i] + '. ' + sentences[i + 1] + '.'
                    chunks.append((source_name, chunk_text))
                
                if len(sentences) % 2 == 1:
                    chunks.append((source_name, sentences[-1] + '.'))
    
    return chunks


def collect_lore_chunks():
    """Collect all chunks from lore files."""
    lore_files = {
        "lore/self": os.path.join(LORE_DIR, "self.md"),
        "lore/user": os.path.join(LORE_DIR, "user.md"),
        "lore/relationship": os.path.join(LORE_DIR, "relationship.md"),
    }
    
    all_chunks = []
    print("\n[LoreIndexer] Scanning lore files...")
    
    for source, path in lore_files.items():
        if os.path.exists(path):
            chunks = chunk_lore_file(path, source)
            all_chunks.extend(chunks)
            print(f"  {source}: {len(chunks)} chunks from {os.path.basename(path)}")
        else:
            print(f"  {source}: FILE NOT FOUND - {path}")
    
    return all_chunks


def main():
    print("=" * 60)
    print("Lore Indexer - Building semantic chunks")
    print("=" * 60)
    
    # Collect lore chunks
    lore_chunks = collect_lore_chunks()
    
    if not lore_chunks:
        print("[LoreIndexer] ERROR: No lore chunks found!")
        sys.exit(1)
    
    print(f"\n[LoreIndexer] Total lore chunks: {len(lore_chunks)}")
    
    # Load existing semantic search to rebuild index with lore
    print("[LoreIndexer] Loading SemanticSearch and rebuilding index...")
    search = SemanticSearch()
    
    # Collect all existing chunks from current index
    existing_chunks = search.chunks if search.chunks else []
    
    # Filter out old lore chunks (keep episodes and semantic memory)
    non_lore_chunks = [c for c in existing_chunks if not c[0].startswith("lore/")]
    
    print(f"[LoreIndexer] Keeping {len(non_lore_chunks)} non-lore chunks")
    
    # Combine: new lore + existing non-lore
    all_chunks = lore_chunks + non_lore_chunks
    
    # Update the search instance
    search.chunks = all_chunks
    
    # Rebuild index
    search.build_index()
    
    print("\n" + "=" * 60)
    print("Indexing complete!")
    print("=" * 60)
    print(f"Total chunks in index: {len(all_chunks)}")
    print(f"  - Lore chunks: {len(lore_chunks)}")
    print(f"  - Other chunks: {len(non_lore_chunks)}")
    print("\nSample lore chunks:")
    for i, (source, text) in enumerate(lore_chunks[:3]):
        preview = text[:80] + "..." if len(text) > 80 else text
        print(f"  [{i+1}] {source}: {preview}")
    if len(lore_chunks) > 3:
        print(f"  ... and {len(lore_chunks) - 3} more")
    print("=" * 60)
    print("\nYou can now use dynamic lore in packet_builder!")


if __name__ == "__main__":
    main()
