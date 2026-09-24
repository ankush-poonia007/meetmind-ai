"""
LangGraph conditional routing logic for MeetMind AI.

Controls transitions between the Supervisor and the 6 specialized sub-agents.
Enforces that agents never call each other directly.
"""

from langgraph.graph import END

from app.core.logging import get_logger
from app.graph.state import MeetMindState

logger = get_logger(__name__)


def route_supervisor(state: MeetMindState) -> str:
    """
    Evaluates state after Supervisor execution to route to the designated sub-agent
    or conclude the graph execution at END.
    """
    if state.get("error"):
        logger.warning(f"Routing to END due to error: {state.get('error')}")
        return END

    action = state.get("session_action", "complete")

    if action == "ingest":
        return "ingestion"
    elif action == "identify":
        return "identity"
    elif action == "extract":
        return "extraction"
    elif action == "confirm":
        # If already confirmed, we are done
        if state.get("confirmation_complete", False):
            return END
        return "confirmation"
    elif action == "qa":
        return "qa"
    elif action == "notify":
        return "notification"
    elif action == "complete":
        return END

    return END
