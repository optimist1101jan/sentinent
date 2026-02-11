import sqlite3
import os

# Get absolute path to database file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "brain.db")

from logger_config import get_logger
logger = get_logger(__name__)

class MemoryStore:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        """Ensures the FTS5 table exists."""
        cursor = self.conn.cursor()
        # Create FTS5 virtual table if it doesn't exist
        # We use 'content' for the text, 'filename' for source, 'timestamp' for import time
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS episodes USING fts5(
                content,
                filename,
                timestamp
            )
        """)
        self.conn.commit()

    def load_from_txt(self, filepath):
        """
        Reads a text file, splits by '---', and ingests chunks.
        Returns number of chunks added.
        """
        if not os.path.exists(filepath):
            return 0

        filename = os.path.basename(filepath)
        count = 0
        
        with open(filepath, "r", encoding="utf-8") as f:
            full_text = f.read()

        # Split by delimiter
        chunks = full_text.split("---")

        cursor = self.conn.cursor()
        for chunk in chunks:
            clean_chunk = chunk.strip()
            if clean_chunk:
                cursor.execute(
                    "INSERT INTO episodes (content, filename, timestamp) VALUES (?, ?, datetime('now'))",
                    (clean_chunk, filename)
                )
                count += 1
        
        self.conn.commit()
        return count

    def search(self, query, limit=3):
        """
        Searches for memories matching the query keywords.
        Returns list of strings.
        """
        if not query or not query.strip():
            return []

        # Basic stop words to ignore in natural language queries
        STOP_WORDS = {
            "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
            "at", "by", "for", "from", "in", "into", "of", "off", "on", "onto",
            "to", "with", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "can", "could", "will",
            "would", "should", "may", "might", "must", "i", "you", "he", "she",
            "it", "we", "they", "my", "your", "his", "her", "its", "our", "their",
            "me", "him", "her", "us", "them", "what", "which", "who", "whom",
            "this", "that", "these", "those", "am", "remember"
        }

        # sanitize input
        safe_query = query.replace('"', '').replace("'", "")
        
        # Tokenize and filter
        tokens = [word for word in safe_query.split() if word.lower() not in STOP_WORDS]
        
        # If all words were stop words (e.g. "do you remember"), fall back to original query split 
        # to find SOMETHING, or just return empty? 
        # Better to try searching for the original words if filtering leaves nothing.
        if not tokens:
            tokens = safe_query.split()

        if not tokens:
             return []

        # Construct FTS5 query with OR operator
        # This allows "do you remember college" to match "college"
        fts_query = " OR ".join(f'"{token}"' for token in tokens)
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT content FROM episodes WHERE content MATCH ? ORDER BY rank LIMIT ?",
                (fts_query, limit)
            )
            results = [row[0] for row in cursor.fetchall()]
            logger.debug(f"Episodic search - Query: \"{query[:50]}\" - Found {len(results)} results")
            return results
        except sqlite3.OperationalError:
            # Fallback if query syntax is invalid for FTS5
            return []

    def wipe_memory(self):
        """Clears all episodes from the database."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM episodes")
        self.conn.commit()
        logger.warning("Memory wiped - All episodes deleted from brain.db")
        print("Brain wiped clean.")

    def add_episode(self, content: str, source: str = "runtime_ingestion"):
        """
        Stage 3: Add a compressed memory directly to the episodes table.
        Called after summarization to "burn" memory into permanent storage.
        
        Args:
            content: The compressed_memory sentence from summarizer
            source: Identifier for the ingestion source (e.g., 'summarizer_cycle_001')
            
        Returns:
            rowid: The SQLite rowid of the inserted episode
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO episodes (content, filename, timestamp) VALUES (?, ?, datetime('now'))",
            (content, source)
        )
        self.conn.commit()
        logger.info(f"Episode added to brain.db - rowid: {cursor.lastrowid} - Source: {source}")
        return cursor.lastrowid

    def close(self):
        self.conn.close()
