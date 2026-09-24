"""
MeetMind AI — Frontend Services Package.

Provides the API client and backend communication layer.
"""

from services.api_client import APIError, MeetMindAPIClient, api

__all__ = [
    "api",
    "MeetMindAPIClient",
    "APIError",
]
