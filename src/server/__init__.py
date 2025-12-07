"""
Server package for the sensor data API.
Provides Flask REST API and data access layer.
"""

from .data_api import DataAPI
from .app import app

__all__ = [
    'DataAPI',
    'app',
]
