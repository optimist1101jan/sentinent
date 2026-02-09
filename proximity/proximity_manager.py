"""
Proximity Manager - proximity/proximity_manager.py

Detects physical/emotional proximity state from user input using embeddings.
Uses Nomic model to classify input against anchor states.
Only injects proximity block when state changes or on first turn.
"""

import os
import sys
import numpy as np

# Get the base directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

# Model path (same as semantic_search)
MODEL_PATH = os.path.join(BASE_DIR, "data", "nomic-embed-text-v1.5.Q8_0.gguf")

# Pre-load llama_cpp with suppressed logging (same pattern as semantic_search)
_Llama = None
_log_callback_ref = None

def _get_llama():
    global _Llama, _log_callback_ref
    if _Llama is None:
        from llama_cpp import llama_log_set
        import ctypes
        
        CB_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p)
        
        def _noop_log_callback(level, text):
            pass
        
        _log_callback_ref = CB_TYPE(_noop_log_callback)
        llama_log_set(_log_callback_ref, None)
        
        from llama_cpp import Llama
        _Llama = Llama
    return _Llama


class ProximityManager:
    """
    Manages proximity state detection and packet injection.
    
    States:
        PHYSICAL: User is physically present, sitting together
        REMOTE: User is chatting remotely (text, phone, discord)
        TRANSITION_AWAY: User is leaving, saying goodbye
        TRANSITION_TOWARD: User is arriving, coming closer
    """
    
    def __init__(self):
        """Initialize the proximity manager with Nomic model and anchor vectors."""
        self.embed_model = None
        self.anchor_vectors = {}
        self.current_state = "REMOTE"  # Default start state
        self.last_injected_state = None
        
        # Define the anchor descriptions for each state
        self.anchors = {
            "PHYSICAL": "search_document: user is sitting together physical presence face to face in the same room close proximity intimate",
            "REMOTE": "search_document: user is texting chatting remotely over phone messaging app discord far away not present",
            "TRANSITION_AWAY": "search_document: user is leaving walking away exiting saying goodbye going out departing",
            "TRANSITION_TOWARD": "search_document: user is arriving entering the room sitting down coming closer approaching"
        }
        
        # Load model and pre-compute anchor vectors
        self._load_model()
        self._precompute_anchors()
    
    def _load_model(self):
        """Load the Nomic embedding model."""
        try:
            if os.path.exists(MODEL_PATH):
                Llama = _get_llama()
                # Suppress stderr during load
                import os as os_module
                null_device = 'nul' if os_module.name == 'nt' else '/dev/null'
                old_stderr_fd = os_module.dup(2)
                with open(null_device, 'w') as devnull:
                    os_module.dup2(devnull.fileno(), 2)
                    try:
                        self.embed_model = Llama(
                            model_path=MODEL_PATH,
                            embedding=True,
                            n_ctx=2048,
                            verbose=False
                        )
                    finally:
                        os_module.dup2(old_stderr_fd, 2)
                        os_module.close(old_stderr_fd)
            else:
                print(f"[ProximityManager] Warning: Model not found at {MODEL_PATH}")
        except Exception as e:
            print(f"[ProximityManager] Warning: Failed to load model: {e}")
    
    def _embed(self, text: str) -> np.ndarray:
        """
        Create embedding for text using Nomic model.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        if self.embed_model:
            embedding = self.embed_model.embed(text, normalize=True)
            return np.array(embedding, dtype='float32')
        else:
            # Fallback: return zero vector
            return np.zeros(768, dtype='float32')
    
    def _precompute_anchors(self):
        """Pre-compute embedding vectors for all anchor states."""
        for state, text in self.anchors.items():
            self.anchor_vectors[state] = self._embed(text)
    
    def detect_state(self, user_input: str, history_context: str = "") -> tuple[str, bool]:
        """
        Detect proximity state from user input.
        
        Args:
            user_input: The current user message
            history_context: Previous context (last message) for short inputs
            
        Returns:
            Tuple of (current_state, did_change)
        """
        # Combine with history context for better detection of short inputs
        if history_context and len(user_input) < 10:
            full_text = f"search_query: {history_context} {user_input}"
        else:
            full_text = f"search_query: {user_input}"
        
        # Create embedding for input
        input_vec = self._embed(full_text)
        
        # Calculate cosine similarity with each anchor
        scores = {}
        input_norm = np.linalg.norm(input_vec)
        
        for state, vec in self.anchor_vectors.items():
            vec_norm = np.linalg.norm(vec)
            if input_norm > 0 and vec_norm > 0:
                similarity = np.dot(input_vec, vec) / (input_norm * vec_norm)
                scores[state] = similarity
            else:
                scores[state] = 0.0
        
        # Get highest scoring state
        detected_state = max(scores, key=scores.get)
        confidence = scores[detected_state]
        
        # Logic gate: Only switch if confidence is high enough
        if confidence > 0.45:
            # Handle transitions
            if detected_state == "TRANSITION_AWAY":
                new_state = "REMOTE"
                changed = (self.current_state != new_state)
                self.current_state = new_state
                return self.current_state, changed
            
            elif detected_state == "TRANSITION_TOWARD":
                new_state = "PHYSICAL"
                changed = (self.current_state != new_state)
                self.current_state = new_state
                return self.current_state, changed
            
            elif detected_state != self.current_state:
                self.current_state = detected_state
                return self.current_state, True
        
        # No change
        return self.current_state, False
    
    def get_proximity_block(self, is_first_turn: bool = False) -> str:
        """
        Get the proximity XML block for packet injection.
        
        Logic:
        - If first turn: FORCE inject
        - If state changed: FORCE inject  
        - Else: Return empty string (tag disappears)
        
        Args:
            is_first_turn: Whether this is the first turn of conversation
            
        Returns:
            XML block string or empty string
        """
        should_inject = False
        
        if is_first_turn:
            should_inject = True
        elif self.current_state != self.last_injected_state:
            should_inject = True
        
        if should_inject:
            self.last_injected_state = self.current_state
            
            # Return context-appropriate description
            if self.current_state == "PHYSICAL":
                context_desc = "AI is right next to them."
            elif self.current_state == "REMOTE":
                context_desc = "AI is speaking through messages or thinking."
            else:
                context_desc = f"Current proximity state: {self.current_state}"
            
            return f"""<distance_context>
{context_desc}
</distance_context>

"""
        else:
            # Return empty - the tag will disappear from packet
            return ""
    
    def get_current_state(self) -> str:
        """Get current proximity state."""
        return self.current_state


# Convenience function for direct usage
def get_proximity_block(user_input: str, is_first_turn: bool = False, 
                        history_context: str = "") -> str:
    """
    Convenience function to get proximity block in one call.
    
    Args:
        user_input: Current user message
        is_first_turn: Whether this is turn 1
        history_context: Previous message for context
        
    Returns:
        Proximity XML block or empty string
    """
    manager = ProximityManager()
    manager.detect_state(user_input, history_context)
    block = manager.get_proximity_block(is_first_turn)
    return block


if __name__ == "__main__":
    # Test the proximity manager
    print("Testing ProximityManager...")
    print("=" * 60)
    
    manager = ProximityManager()
    
    test_inputs = [
        ("hi", True, "First turn - should inject"),
        ("how are you", False, "No change"),
        ("walks over to you", False, "Transition toward"),
        ("sits next to you", False, "Still physical"),
        ("ok", False, "Short input with context"),
        ("I need to go now", False, "Leaving"),
        ("bye", False, "Goodbye"),
        ("texts from work", False, "Remote"),
    ]
    
    prev_input = ""
    for i, (text, is_first, desc) in enumerate(test_inputs):
        print(f"\nTest {i+1}: \"{text}\" ({desc})")
        state, changed = manager.detect_state(text, prev_input)
        block = manager.get_proximity_block(is_first)
        print(f"  Detected state: {state} (changed: {changed})")
        print(f"  Block length: {len(block)} chars")
        if block:
            print(f"  Block preview: {block[:100]}...")
        prev_input = text
    
    print("\n" + "=" * 60)
    print("Tests complete!")
