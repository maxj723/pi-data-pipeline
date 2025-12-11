"""
Base class for all decision models.
"""

from abc import ABC, abstractmethod
from typing import Any
from .decision import Decision


class BaseDecisionModel(ABC):
    """
    Abstract base class for all decision models.

    All decision models must implement the analyze() method
    and return Decision objects.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize the decision model.

        Args:
            config: Optional configuration dictionary.
        """
        self.config = config or {}
        self.model_type = self.__class__.__name__

    @abstractmethod
    def analyze(self, reading: dict[str, Any]) -> Decision:
        """
        Analyze a single sensor reading and produce a decision.

        Args:
            reading: Dictionary containing sensor data.

        Returns:
            Decision object with standardized output.
        """
        pass

    def analyze_batch(self, readings: list[dict[str, Any]]) -> list[Decision]:
        """
        Analyze multiple sensor readings.

        Args:
            readings: List of sensor reading dictionaries.

        Returns:
            List of Decision objects.
        """
        return [self.analyze(reading) for reading in readings]

    def update_config(self, new_config: dict[str, Any]) -> None:
        """
        Update the model configuration.

        Args:
            new_config: New configuration to merge with existing config.
        """
        self.config.update(new_config)

    def get_config(self) -> dict[str, Any]:
        """
        Get the current model configuration.

        Returns:
            Copy of the current configuration.
        """
        return self.config.copy()
