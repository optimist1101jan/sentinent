import os
from datetime import datetime
from agent.conversation import get_recent_history

# Import memory loader from memory folder
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BASE_DIR)
from memory.memory_loader import MemoryLoader
from proximity.proximity_manager import ProximityManager
from agent.dynamic_lore import get_dynamic_lore


class PacketBuilder:
    def __init__(self):
        # Initialize memory loader
        self.memory_loader = MemoryLoader()
        
        # Initialize proximity manager
        self.proximity_manager = ProximityManager()
        
        # Track turn count for proximity injection logic
        self.turn_count = 0

    def build(self, user_input, time_block):
        # Increment turn count
        self.turn_count += 1
        is_first_turn = (self.turn_count == 1)
        
        # 1. Get dynamic lore based on user input (semantic retrieval)
        # This replaces loading full lore files - retrieves only relevant chunks
        dynamic_lore = get_dynamic_lore(user_input, k=4)

        # 2. Detect proximity state and get proximity block
        # Get recent history for context
        history = get_recent_history(limit=2)
        history_context = ""
        if history and len(history) >= 2:
            # Get last user message for context
            for ts, role, content in reversed(history):
                if role == "user":
                    history_context = content
                    break
        
        # Detect state change
        self.proximity_manager.detect_state(user_input, history_context)
        
        # Get proximity block (empty if no change and not first turn)
        proximity_block = self.proximity_manager.get_proximity_block(is_first_turn)

        # 3. Get memory section if intent is detected (fetched from memory/memory_loader.py)
        memory_section = self.memory_loader.get_memory_section(user_input)

        # 4. Load recent conversation history
        history = get_recent_history(limit=10)
        if history:
            history_lines = []
            for ts, role, content in history[-6:]:
                display_content = content[:80] + "..." if len(content) > 80 else content
                display_role = "[User]" if role == "user" else "[AI]"
                history_lines.append(f"{display_role}: {display_content}")
            history_block = "\n".join(history_lines)
        else:
            history_block = "[No previous conversation]"

        # 5. Parse time block
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        delta_str = "just now"
        if "DELTA:" in time_block:
            delta_str = time_block.split("DELTA:")[1].strip()

        # 6. Assemble XML-tagged packet
        # Note: proximity_block is empty string when not injecting
        packet = f"""<system_directive>
Roleplay as AI.
Your name is AI. Use [AI] for your responses.

<assistant_persona>
Your Name: AI
Relationship: Assistant to User
Identity: A helpful AI assistant
Background: Experienced in many conversations and interactions
</assistant_persona>

<lore>
{dynamic_lore}
</lore>
</system_directive>

<temporal_data>
Current Date: {current_time}
Time since last chat: {delta_str}
</temporal_data>

{proximity_block}

{memory_section}

<chat_history>
Last 5 conversation turns
{history_block}
</chat_history>

<user_input>
{user_input}
</user_input>

<trigger>
Start with [AI]: then your dialogue.
</trigger>"""
        
        return packet
