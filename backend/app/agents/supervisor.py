"""
Supervisor Agent for MeetMind AI.

Pattern: Plan-and-Execute
Model: gemini-3.6-flash (via ProviderGateway with use_case="supervisor")

Responsibilities:
- Reads meeting and session context from state and database.
- Generates a structured execution plan before routing.
- Routes execution through the LangGraph state machine.
- Aggregates sub-agent outputs into final responses.
- Does NOT directly perform chunking, embedding, retrieval, or persistence.
"""

from typing import Any, Optional
from app.core.config import SUPERVISOR_MODEL
from app.core.logging import get_logger
from app.graph.state import MeetMindState

logger = get_logger(__name__)


class SupervisorAgent:
    """
    Supervisor Agent coordinating the multi-agent execution pipeline.
    Implements Plan-and-Execute pattern to determine and monitor execution stages.
    """

    model_name: str = SUPERVISOR_MODEL

    @classmethod
    def generate_execution_plan(cls, state: MeetMindState) -> list[str]:
        """
        Determines the ordered list of remaining agent stages based on session_action
        and completed stage indicators in the state.
        """
        action = state.get("session_action")

        if action == "qa":
            return ["qa"]
        if action == "notify":
            return ["notification"]
        if action == "confirm":
            return ["confirmation"]

        # Main meeting processing pipeline
        plan: list[str] = []
        if not state.get("ingestion_complete", False):
            plan.append("ingestion")
        if not state.get("identity_confirmed", False):
            plan.append("identity")
        if not state.get("extraction_complete", False):
            plan.append("extraction")
        if not state.get("confirmation_complete", False):
            plan.append("confirmation")

        return plan

    @classmethod
    def route_to_agent_tool(cls, state: MeetMindState) -> str:
        """
        Tool determining the next agent node to execute based on state.
        Returns: 'ingestion' | 'identity' | 'extraction' | 'confirmation' | 'qa' | 'notification' | 'complete'
        """
        if state.get("error"):
            logger.warning(f"Supervisor encountered error state: {state.get('error')}")
            return "complete"

        action = state.get("session_action")
        if action == "qa":
            return "qa"
        if action in ("notify", "notification"):
            return "notification"
        if action in ("confirm", "confirmation"):
            if state.get("confirmation_complete", False):
                return "complete"
            return "confirmation"
        if action == "complete":
            return "complete"

        plan = cls.generate_execution_plan(state)
        if not plan:
            return "complete"

        return plan[0]

    @classmethod
    def aggregate_response_tool(cls, state: MeetMindState) -> str:
        """
        Tool combining sub-agent outputs into a structured summary for the client.
        """
        action = state.get("session_action")
        if action == "qa":
            return state.get("qa_answer", "No answer generated.")
        if action == "notify":
            alerts = state.get("alerts_sent", 0)
            return f"Notification run complete: {alerts} deadline alerts delivered."

        tasks_saved = state.get("saved_tasks", 0)
        extracted = len(state.get("extracted_tasks", []))
        highlights = len(state.get("extracted_highlights", []))
        confirmation = state.get("user_confirmation", "pending")

        return (
            f"Meeting processing complete for meeting {state.get('meeting_id')}. "
            f"Extracted {extracted} tasks and {highlights} highlights. "
            f"Confirmation status: {confirmation} ({tasks_saved} tasks saved)."
        )

    @classmethod
    def run(cls, state: MeetMindState) -> dict[str, Any]:
        """
        Executes Supervisor reasoning: updates execution plan, current stage,
        and next session_action.
        """
        logger.info(
            f"Supervisor evaluating state for meeting {state.get('meeting_id')}, "
            f"current action: {state.get('session_action')}"
        )

        plan = cls.generate_execution_plan(state)
        next_step = cls.route_to_agent_tool(state)

        # Map next_step to session_action
        action_map = {
            "ingestion": "ingest",
            "identity": "identify",
            "extraction": "extract",
            "confirmation": "confirm",
            "qa": "qa",
            "notification": "notify",
            "complete": "complete",
        }
        next_action = action_map.get(next_step, "complete")

        updates: dict[str, Any] = {
            "current_stage": "supervisor",
            "execution_plan": plan,
            "session_action": next_action,
        }

        if next_action == "complete":
            updates["final_response"] = cls.aggregate_response_tool(state)

        logger.info(f"Supervisor planned stages: {plan}, next routing: {next_step}")
        return updates
