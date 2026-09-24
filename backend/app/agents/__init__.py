"""
MeetMind AI 7-Agent Roster.

1. SupervisorAgent (Plan-and-Execute)
2. IngestionAgent (ReAct)
3. IdentityAgent (Form-First Identity Context)
4. ExtractionAgent (ReAct)
5. ConfirmationAgent (ReAct + Human-in-the-Loop)
6. QAAgent (ReAct + Hybrid RAG)
7. NotificationAgent (ReAct + Resend Alerting)
"""

from app.agents.confirmation import ConfirmationAgent
from app.agents.extraction import ExtractionAgent
from app.agents.identity import IdentityAgent
from app.agents.ingestion import IngestionAgent
from app.agents.notification import NotificationAgent, run_notification_agent
from app.agents.qa import QAAgent, run_qa_agent
from app.agents.supervisor import SupervisorAgent

__all__ = [
    "SupervisorAgent",
    "IngestionAgent",
    "IdentityAgent",
    "ExtractionAgent",
    "ConfirmationAgent",
    "QAAgent",
    "NotificationAgent",
    "run_qa_agent",
    "run_notification_agent",
]
