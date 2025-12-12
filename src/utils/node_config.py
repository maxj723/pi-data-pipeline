"""
Utility functions for loading and accessing node configuration.

This module provides centralized access to node location and metadata,
used by the weather service, heat map, and all location-based features.
"""

import json
from pathlib import Path
from typing import Optional, Any


def get_config_path() -> Path:
    """
    Get the path to the nodes configuration file.

    Returns:
        Path to config/nodes.json
    """
    # Get project root (3 levels up from this file)
    project_root = Path(__file__).parent.parent.parent
    return project_root / 'config' / 'nodes.json'


def load_node_config() -> list[dict[str, Any]]:
    """
    Load node configuration from config/nodes.json.

    Returns:
        List of node dictionaries with location and metadata.
        Returns empty list if file doesn't exist or can't be parsed.
    """
    config_path = get_config_path()

    try:
        if not config_path.exists():
            print(f"[WARNING] Node config file not found: {config_path}")
            return []

        with open(config_path, 'r') as f:
            nodes = json.load(f)

        if not isinstance(nodes, list):
            print(f"[WARNING] Node config should be a list, got {type(nodes)}")
            return []

        return nodes

    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse node config: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to load node config: {e}")
        return []


def get_node_location(node_id: str) -> Optional[dict[str, Any]]:
    """
    Get location and metadata for a specific node.

    Args:
        node_id: The node ID to look up (e.g., "!512397a3")

    Returns:
        Node dictionary if found, None otherwise.
        Dictionary includes: node_id, name, lat, lon
    """
    nodes = load_node_config()

    for node in nodes:
        if node.get('node_id') == node_id:
            return node

    return None


def get_all_nodes() -> list[dict[str, Any]]:
    """
    Get all nodes from configuration.

    Returns:
        List of all node dictionaries.
    """
    return load_node_config()


def validate_node_config() -> tuple[bool, list[str]]:
    """
    Validate the node configuration file.

    Checks that:
    - File exists and is valid JSON
    - All nodes have required fields: node_id, name, lat, lon
    - Coordinates are valid (lat: -90 to 90, lon: -180 to 180)

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check file exists
    config_path = get_config_path()
    if not config_path.exists():
        errors.append(f"Config file not found: {config_path}")
        return (False, errors)

    # Load and validate structure
    try:
        nodes = load_node_config()
        if not nodes:
            errors.append("Config file is empty or invalid")
            return (False, errors)

        # Validate each node
        required_fields = ['node_id', 'name', 'lat', 'lon']
        for i, node in enumerate(nodes):
            # Check required fields
            for field in required_fields:
                if field not in node:
                    errors.append(f"Node {i}: Missing required field '{field}'")

            # Validate coordinates
            if 'lat' in node:
                try:
                    lat = float(node['lat'])
                    if not -90 <= lat <= 90:
                        errors.append(f"Node {i} ({node.get('node_id', 'unknown')}): Invalid latitude {lat}")
                except (ValueError, TypeError):
                    errors.append(f"Node {i} ({node.get('node_id', 'unknown')}): Latitude must be a number")

            if 'lon' in node:
                try:
                    lon = float(node['lon'])
                    if not -180 <= lon <= 180:
                        errors.append(f"Node {i} ({node.get('node_id', 'unknown')}): Invalid longitude {lon}")
                except (ValueError, TypeError):
                    errors.append(f"Node {i} ({node.get('node_id', 'unknown')}): Longitude must be a number")

        return (len(errors) == 0, errors)

    except Exception as e:
        errors.append(f"Validation error: {e}")
        return (False, errors)
