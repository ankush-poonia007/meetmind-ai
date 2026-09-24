"""
MeetMind AI LangGraph Multi-Agent StateGraph.

Frozen Architecture:
- 7 Agents: Supervisor, Ingestion, Identity, Extraction, Confirmation, Q&A, Notification.
- Main Pipeline: START -> Supervisor -> Ingestion -> Identity -> Extraction -> Confirmation (HITL Interrupt) -> RESUME -> END.
- Q&A Path: START -> Supervisor -> Q&A -> END.
- Notification Path: START -> Supervisor -> Notification -> END.
- Agents NEVER call each other directly; Supervisor and StateGraph orchestrate all routing.
- Real HITL Pause & Resume mediated by LangGraph interrupt() and checkpointer.
"""

import contextvars
from typing import Any, Optional
from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agents.confirmation import ConfirmationAgent
from app.agents.extraction import ExtractionAgent
from app.agents.identity import IdentityAgent
from app.agents.ingestion import IngestionAgent
from app.agents.notification import NotificationAgent
from app.agents.qa import QAAgent
from app.agents.supervisor import SupervisorAgent
from app.core.exceptions import InvalidStateError
from app.core.logging import get_logger
from app.graph.router import route_supervisor
from app.graph.state import MeetMindState

logger = get_logger(__name__)

# Context variable to propagate synchronous DB session across graph nodes
_active_db_session: contextvars.ContextVar[Optional[Any]] = contextvars.ContextVar(
    "_active_db_session", default=None
)


def _get_active_db() -> Optional[Any]:
    return _active_db_session.get()


# ── Node Definitions ─────────────────────────────────────────────────────────

def supervisor_node(state: MeetMindState) -> dict[str, Any]:
    """Invokes Supervisor Agent to plan and route execution."""
    return SupervisorAgent.run(state)


def ingestion_node(state: MeetMindState) -> dict[str, Any]:
    """Invokes Ingestion Agent to parse, chunk, and embed transcript."""
    db = _get_active_db()
    if db is not None:
        return IngestionAgent.run(state, db=db)
    from app.db.session import SessionLocal
    sess = SessionLocal()
    try:
        return IngestionAgent.run(state, db=sess)
    finally:
        sess.close()


def identity_node(state: MeetMindState) -> dict[str, Any]:
    """Invokes Identity Agent to resolve user mentions form-first."""
    db = _get_active_db()
    if db is not None:
        return IdentityAgent.run(state, db=db)
    from app.db.session import SessionLocal
    sess = SessionLocal()
    try:
        return IdentityAgent.run(state, db=sess)
    finally:
        sess.close()


def extraction_node(state: MeetMindState) -> dict[str, Any]:
    """Invokes Extraction Agent to extract tasks and highlights."""
    db = _get_active_db()
    if db is not None:
        return ExtractionAgent.run(state, db=db)
    from app.db.session import SessionLocal
    sess = SessionLocal()
    try:
        return ExtractionAgent.run(state, db=sess)
    finally:
        sess.close()


def confirmation_node(state: MeetMindState) -> dict[str, Any]:
    """Invokes Confirmation Agent (with HITL interrupt)."""
    db = _get_active_db()
    if db is not None:
        return ConfirmationAgent.run(state, db=db)
    from app.db.session import SessionLocal
    sess = SessionLocal()
    try:
        return ConfirmationAgent.run(state, db=sess)
    finally:
        sess.close()


def qa_node(state: MeetMindState) -> dict[str, Any]:
    """Invokes Q&A Agent with meeting-scoped hybrid RAG."""
    db = _get_active_db()
    if db is not None:
        return QAAgent.run(state, db=db)
    from app.db.session import SessionLocal
    sess = SessionLocal()
    try:
        return QAAgent.run(state, db=sess)
    finally:
        sess.close()


def notification_node(state: MeetMindState) -> dict[str, Any]:
    """Invokes Notification Agent to process deadline alerts."""
    db = _get_active_db()
    if db is not None:
        return NotificationAgent.run(state, db=db)
    from app.db.session import SessionLocal
    sess = SessionLocal()
    try:
        return NotificationAgent.run(state, db=sess)
    finally:
        sess.close()


# ── Graph Builder ────────────────────────────────────────────────────────────

def build_meetmind_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """
    Constructs and compiles the unified MeetMind AI multi-agent StateGraph.
    """
    builder = StateGraph(MeetMindState)

    # 1. Register all 7 nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("ingestion", ingestion_node)
    builder.add_node("identity", identity_node)
    builder.add_node("extraction", extraction_node)
    builder.add_node("confirmation", confirmation_node)
    builder.add_node("qa", qa_node)
    builder.add_node("notification", notification_node)

    # 2. Graph entry point: always begins with Supervisor
    builder.add_edge(START, "supervisor")

    # 3. Conditional routing from Supervisor
    builder.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "ingestion": "ingestion",
            "identity": "identity",
            "extraction": "extraction",
            "confirmation": "confirmation",
            "qa": "qa",
            "notification": "notification",
            END: END,
        },
    )

    # 4. Return edges: all sub-agents route strictly back to Supervisor
    builder.add_edge("ingestion", "supervisor")
    builder.add_edge("identity", "supervisor")
    builder.add_edge("extraction", "supervisor")
    builder.add_edge("confirmation", "supervisor")
    builder.add_edge("qa", "supervisor")
    builder.add_edge("notification", "supervisor")

    # 5. Compile with checkpointer for HITL state persistence
    chk = checkpointer if checkpointer is not None else MemorySaver()
    return builder.compile(checkpointer=chk)


# Global singleton compiled graph with in-memory checkpointer
global_checkpointer = MemorySaver()
meetmind_graph = build_meetmind_graph(checkpointer=global_checkpointer)


# ── High-Level Graph Runner Helpers ──────────────────────────────────────────

def run_extraction_graph(
    meeting_id: UUID,
    user_id: UUID,
    db: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Executes the main pipeline graph up to the confirmation interrupt:
    Supervisor -> Ingestion -> Identity -> Extraction -> Confirmation (PAUSE).

    Returns extracted preview dictionary:
    {"tasks": [...], "highlights": [...]}
    """
    meeting_id_str = str(meeting_id)
    thread_id = f"meeting_{meeting_id_str}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: MeetMindState = {
        "meeting_id": meeting_id_str,
        "user_id": str(user_id),
        "session_action": "ingest",
        "ingestion_complete": False,
        "identity_confirmed": False,
        "extraction_complete": False,
        "confirmation_complete": False,
    }

    token = _active_db_session.set(db)
    try:
        # Run graph until interrupt
        result = meetmind_graph.invoke(initial_state, config=config)

        # Retrieve paused state values from checkpointer
        state_snapshot = meetmind_graph.get_state(config)
        state_values = state_snapshot.values if state_snapshot else result

        tasks = state_values.get("extracted_tasks", [])
        highlights = state_values.get("extracted_highlights", [])

        return {
            "tasks": tasks,
            "highlights": highlights,
            "meeting_id": meeting_id_str,
            "user_id": str(user_id),
        }
    finally:
        _active_db_session.reset(token)


def resume_extraction_graph(
    meeting_id: UUID,
    user_id: UUID,
    confirmation: str,
    confirmed_task_ids: Optional[list[str]] = None,
    db: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Resumes a paused extraction pipeline at the Confirmation Agent stage:
    RESUME -> Confirmation (Persist) -> Supervisor -> END.

    Enforces duplicate confirmation safety.
    """
    meeting_id_str = str(meeting_id)
    thread_id = f"meeting_{meeting_id_str}"
    config = {"configurable": {"thread_id": thread_id}}

    # Inspect current state
    state_snapshot = meetmind_graph.get_state(config)
    if not state_snapshot or not state_snapshot.values:
        # If no paused state found in checkpointer, fallback to service cache
        logger.info(f"No active paused graph state for {thread_id}; invoking directly")
        from app.agents.confirmation import ConfirmationAgent
        from app.services.extraction_service import _EXTRACTION_PREVIEWS
        cached = _EXTRACTION_PREVIEWS.get(meeting_id_str, {"tasks": [], "highlights": []})
        direct_state: MeetMindState = {
            "meeting_id": meeting_id_str,
            "user_id": str(user_id),
            "user_confirmation": confirmation,
            "confirmed_task_ids": confirmed_task_ids or [],
            "extracted_tasks": cached.get("tasks", []),
            "extracted_highlights": cached.get("highlights", []),
            "confirmation_complete": False,
        }
        return ConfirmationAgent.run(direct_state, db=db)

    # Check for duplicate confirmation: if confirmation_complete is True
    if state_snapshot.values.get("confirmation_complete", False):
        raise InvalidStateError(
            f"Confirmation has already been completed for meeting '{meeting_id_str}'."
        )

    resume_payload = {
        "user_confirmation": confirmation,
        "confirmed_task_ids": confirmed_task_ids or [],
    }

    token = _active_db_session.set(db)
    try:
        result = meetmind_graph.invoke(Command(resume=resume_payload), config=config)
        return result
    finally:
        _active_db_session.reset(token)


def run_qa_graph(
    meeting_id: UUID,
    user_id: UUID,
    question: str,
    user_name: str,
    user_role: Optional[str] = None,
    db: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Executes the Q&A graph path:
    Supervisor -> Q&A Agent (Hybrid RAG) -> Supervisor -> END.
    """
    meeting_id_str = str(meeting_id)
    import uuid
    thread_id = f"qa_{meeting_id_str}_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    qa_state: MeetMindState = {
        "meeting_id": meeting_id_str,
        "user_id": str(user_id),
        "session_action": "qa",
        "user_question": question,
        "user_name": user_name,
        "user_role": user_role or "",
    }

    token = _active_db_session.set(db)
    try:
        return meetmind_graph.invoke(qa_state, config=config)
    finally:
        _active_db_session.reset(token)


def run_notification_graph(
    db: Optional[Any] = None,
    trigger: str = "scheduled",
) -> dict[str, Any]:
    """
    Executes the Notification graph path:
    Supervisor -> Notification Agent -> Supervisor -> END.
    """
    import uuid
    thread_id = f"notification_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    notif_state: MeetMindState = {
        "session_action": "notify",
        "meeting_id": "",
        "user_id": "",
    }

    token = _active_db_session.set(db)
    try:
        return meetmind_graph.invoke(notif_state, config=config)
    finally:
        _active_db_session.reset(token)
