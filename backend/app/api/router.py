"""
Central API router aggregator for MeetMind AI.

Registers the /api/v1 prefix and acts as the mount point for domain routers.
Domain routers (meetings, tasks, chat, extraction, etc.) will be attached
in Gate 5 as business endpoints are implemented.
"""

from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")
