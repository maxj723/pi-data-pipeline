"""
Local file-based storage for decisions.

Stores decisions as they are generated in a JSON file for later retrieval.
"""

import json
import os
from threading import Lock
from typing import Any
from pathlib import Path


class DecisionStorage:
    """Thread-safe local file storage for decisions."""

    def __init__(self, file_path: str | None = None):
        """
        Initialize decision storage.

        Args:
            file_path: Path to the JSON file for storing decisions.
                      If None, uses default path in data/decisions.json
        """
        if file_path is None:
            # Default to project root/data/decisions.json
            project_root = Path(__file__).parent.parent.parent
            self.file_path = project_root / 'data' / 'decisions.json'
        else:
            self.file_path = Path(file_path)

        self._lock = Lock()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Ensure the data directory and file exist."""
        # Create directory if it doesn't exist
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create empty file if it doesn't exist (use dict format)
        if not self.file_path.exists():
            with open(self.file_path, 'w') as f:
                json.dump({}, f)

    def save_decision(self, decision_dict: dict[str, Any]) -> bool:
        """
        Save a decision to the storage file.

        Maintains one decision per node_id. If the decision is the same as the
        existing one (excluding timestamp), only the timestamp is updated.

        Args:
            decision_dict: Decision dictionary to save.

        Returns:
            True if successful, False otherwise.
        """
        try:
            with self._lock:
                node_id = decision_dict.get('node_id')
                if not node_id:
                    print("Error: Decision missing node_id")
                    return False

                # Read existing decisions (stored as dict with node_id as key)
                with open(self.file_path, 'r') as f:
                    try:
                        decisions_dict = json.load(f)
                        # Handle legacy format (list) - convert to dict
                        if isinstance(decisions_dict, list):
                            decisions_dict = {d['node_id']: d for d in decisions_dict if 'node_id' in d}
                    except json.JSONDecodeError:
                        decisions_dict = {}

                # Check if we already have a decision for this node
                if node_id in decisions_dict:
                    existing = decisions_dict[node_id]

                    # Compare decisions (excluding timestamp)
                    new_without_timestamp = {k: v for k, v in decision_dict.items() if k != 'timestamp'}
                    existing_without_timestamp = {k: v for k, v in existing.items() if k != 'timestamp'}

                    if new_without_timestamp == existing_without_timestamp:
                        # Same decision - just update timestamp
                        existing['timestamp'] = decision_dict['timestamp']
                        print(f"  → Updated timestamp for {node_id}: {existing['decision_text']}")
                    else:
                        # Different decision - replace it
                        decisions_dict[node_id] = decision_dict
                        print(f"  → Updated decision for {node_id}: {decision_dict['decision_text']}")
                else:
                    # New node - add it
                    decisions_dict[node_id] = decision_dict
                    print(f"  → New decision for {node_id}: {decision_dict['decision_text']}")

                # Write back to file
                with open(self.file_path, 'w') as f:
                    json.dump(decisions_dict, f, indent=2)

                return True

        except Exception as e:
            print(f"Error saving decision: {e}")
            return False

    def get_all_decisions(self) -> list[dict[str, Any]]:
        """
        Get all decisions from storage.

        Returns:
            List of decision dictionaries (one per node).
        """
        try:
            with self._lock:
                with open(self.file_path, 'r') as f:
                    try:
                        data = json.load(f)
                        # Handle both dict and legacy list formats
                        if isinstance(data, dict):
                            return list(data.values())
                        else:
                            return data
                    except json.JSONDecodeError:
                        return []
        except Exception as e:
            print(f"Error reading decisions: {e}")
            return []

    def clear_all(self) -> int:
        """
        Clear all decisions from storage.

        Returns:
            Number of decisions cleared.
        """
        try:
            with self._lock:
                # Count existing decisions
                with open(self.file_path, 'r') as f:
                    try:
                        data = json.load(f)
                        if isinstance(data, dict):
                            count = len(data)
                        else:
                            count = len(data)
                    except json.JSONDecodeError:
                        count = 0

                # Clear the file (use dict format)
                with open(self.file_path, 'w') as f:
                    json.dump({}, f)

                return count

        except Exception as e:
            print(f"Error clearing decisions: {e}")
            return 0

    def get_count(self) -> int:
        """
        Get the number of stored decisions.

        Returns:
            Number of decisions in storage.
        """
        return len(self.get_all_decisions())
