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

        # Create empty file if it doesn't exist
        if not self.file_path.exists():
            with open(self.file_path, 'w') as f:
                json.dump([], f)

    def save_decision(self, decision_dict: dict[str, Any]) -> bool:
        """
        Save a decision to the storage file.

        Args:
            decision_dict: Decision dictionary to save.

        Returns:
            True if successful, False otherwise.
        """
        try:
            with self._lock:
                # Read existing decisions
                with open(self.file_path, 'r') as f:
                    try:
                        decisions = json.load(f)
                    except json.JSONDecodeError:
                        decisions = []

                # Append new decision
                decisions.append(decision_dict)

                # Write back to file
                with open(self.file_path, 'w') as f:
                    json.dump(decisions, f, indent=2)

                return True

        except Exception as e:
            print(f"Error saving decision: {e}")
            return False

    def get_all_decisions(self) -> list[dict[str, Any]]:
        """
        Get all decisions from storage.

        Returns:
            List of decision dictionaries.
        """
        try:
            with self._lock:
                with open(self.file_path, 'r') as f:
                    try:
                        return json.load(f)
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
                        decisions = json.load(f)
                        count = len(decisions)
                    except json.JSONDecodeError:
                        count = 0

                # Clear the file
                with open(self.file_path, 'w') as f:
                    json.dump([], f)

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
