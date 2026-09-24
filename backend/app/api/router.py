"""
Central API router aggregator for MeetMind AI.

Registers the /api/v1 prefix and aggregates all 7 domain routers:
- users: /api/v1/users
- meetings: /api/v1/meetings
- tasks: /api/v1/tasks
- chat: /api/v1/chat
- extraction: /api/v1/extraction
- highlights: /api/v1/highlights
- notifications: /api/v1/notifications
"""

from fastapi import APIRouter

from app.api.chat import router as chat_router
from app.api.extraction import router as extraction_router
from app.api.highlights import router as highlights_router
from app.api.meetings import router as meetings_router
from app.api.notifications import router as notifications_router
from app.api.tasks import router as tasks_router
from app.api.users import router as users_router

api_router = APIRouter(prefix="/api/v1")

# Mount all 7 domain routers
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(meetings_router, prefix="/meetings", tags=["meetings"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(extraction_router, prefix="/extraction", tags=["extraction"])
api_router.include_router(highlights_router, prefix="/highlights", tags=["highlights"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
