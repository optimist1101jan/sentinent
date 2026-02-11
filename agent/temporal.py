import json
import os
from datetime import datetime

TIME_DB_PATH = "agent/timestamps.json"

class TimeManager:
    def __init__(self):
        self.now = datetime.now()
        self.last_interaction = None
        self.delta_str = "First Run"

    def load_and_update(self):
        """Loads last time, calculates delta, saves current time."""
        data = {}
        
        # Load previous state
        if os.path.exists(TIME_DB_PATH):
            try:
                with open(TIME_DB_PATH, "r") as f:
                    data = json.load(f)
                    if "last_interaction" in data:
                        self.last_interaction = datetime.fromisoformat(data["last_interaction"])
            except (json.JSONDecodeError, ValueError):
                pass # Corrupt or empty file, treat as fresh

        # Calculate Delta
        if self.last_interaction:
            delta = self.now - self.last_interaction
            hours = delta.total_seconds() / 3600
            if hours < 1:
                self.delta_str = f"{int(delta.total_seconds() / 60)} minutes"
            elif hours < 24:
                self.delta_str = f"{hours:.1f} hours"
            else:
                days = delta.days
                self.delta_str = f"{days} days"
        else:
            self.delta_str = "No prior record"
        # 3. Ensure Directory Exists (The Fix)
        directory = os.path.dirname(TIME_DB_PATH)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        # Save Current State (Simulating DB write)
        with open(TIME_DB_PATH, "w") as f:
            json.dump({"last_interaction": self.now.isoformat()}, f)

    def get_time_block(self):
        """Returns the formatted string block for the packet."""
        last_str = self.last_interaction.strftime("%Y-%m-%d %H:%M") if self.last_interaction else "N/A"
        
        return (
            f"CURRENT_TIME: {self.now.strftime('%Y-%m-%d %H:%M')} (Day {self.now.weekday() + 1})\n"
            f"LAST_INTERACTION: {last_str}\n"
            f"DELTA: {self.delta_str}"
        )