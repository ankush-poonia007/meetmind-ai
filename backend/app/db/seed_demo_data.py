"""
MeetMind AI — Batch 4.9: Deterministic Demo Data Seeding System.

Phase: 4 — Authentication, User Isolation & Dashboard Integration
Batch: 4.9 — Four Demo Accounts & Realistic Test Data

Provides:
- Deterministic UUIDv5 identifiers derived from fixed SEED_NAMESPACE.
- Creation of 4 departmental demo accounts (Engineering, Product, Operations, HR).
- Explicit environment-variable password provisioning with Argon2id hashing.
- Zero fallback passwords — fails safely if required environment variables are missing.
- Relative deadline anchoring with millisecond precision (23:59:59.999000).
- Idempotent and non-destructive updates preserving evaluator-created records.
- CLI options: --timezone, --reset-passwords, --reset-task-status, --reseed-demo-data.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Final
import zoneinfo

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import hash_password, validate_password_complexity
from app.db.models.highlight import Highlight
from app.db.models.meeting import Meeting
from app.db.models.meeting_participant import MeetingParticipant
from app.db.models.task import Task, TaskPriority, TaskStatus
from app.db.models.user import User
from app.db.models.user_credentials import UserCredentials
from app.db.session import SessionLocal

# Ensure environment variables from .env are loaded
load_dotenv()

logger = get_logger(__name__)

# ── Deterministic UUIDv5 Namespace ──────────────────────────────────────────
SEED_NAMESPACE: Final[uuid.UUID] = uuid.uuid5(uuid.NAMESPACE_DNS, "seed.meetmind.ai")


def get_demo_user_id(account_key: str) -> uuid.UUID:
    """Generates a deterministic UUIDv5 for a demo user account."""
    return uuid.uuid5(SEED_NAMESPACE, f"user:{account_key}")


def get_demo_meeting_id(account_key: str, meeting_index: int) -> uuid.UUID:
    """Generates a deterministic UUIDv5 for a demo meeting."""
    return uuid.uuid5(SEED_NAMESPACE, f"meeting:{account_key}:{meeting_index}")


def get_demo_participant_id(account_key: str, meeting_index: int, participant_index: int) -> uuid.UUID:
    """Generates a deterministic UUIDv5 for a demo meeting participant."""
    return uuid.uuid5(
        SEED_NAMESPACE, f"participant:{account_key}:{meeting_index}:{participant_index}"
    )


def get_demo_task_id(account_key: str, task_index: int) -> uuid.UUID:
    """Generates a deterministic UUIDv5 for a demo task."""
    return uuid.uuid5(SEED_NAMESPACE, f"task:{account_key}:{task_index}")


def get_demo_highlight_id(account_key: str, highlight_index: int) -> uuid.UUID:
    """Generates a deterministic UUIDv5 for a demo highlight."""
    return uuid.uuid5(SEED_NAMESPACE, f"highlight:{account_key}:{highlight_index}")


# ── Timezone Resolution & Deadline Helpers ──────────────────────────────────
def resolve_seeder_timezone(cli_tz: str | None = None) -> zoneinfo.ZoneInfo:
    """
    Resolves target timezone following the strict precedence:
    1. CLI flag (--timezone)
    2. Environment variable (DEMO_DATA_TIMEZONE)
    3. Default to UTC
    """
    tz_str = cli_tz or os.getenv("DEMO_DATA_TIMEZONE") or "UTC"
    tz_str = tz_str.strip()
    try:
        return zoneinfo.ZoneInfo(tz_str)
    except Exception as exc:
        raise ValueError(
            f"Invalid timezone specification '{tz_str}'. Must be a valid IANA timezone string "
            f"(e.g., 'Asia/Kolkata', 'America/New_York', 'UTC')."
        ) from exc


def compute_due_today_deadline(target_now: datetime) -> datetime:
    """
    Computes a UTC timestamp anchored strictly to 23:59:59.999 in the target timezone.
    Matches JavaScript Date millisecond precision (avoids premature expiration edge case).
    """
    target_today = target_now.date()
    target_end_of_day = datetime.combine(
        target_today, time(23, 59, 59, 999000), tzinfo=target_now.tzinfo
    )
    return target_end_of_day.astimezone(timezone.utc)


# ── Seeder Execution Tracking ────────────────────────────────────────────────
@dataclass
class SeederReport:
    users_created: int = 0
    users_updated: int = 0
    users_skipped: int = 0
    passwords_reset: int = 0
    meetings_created: int = 0
    meetings_updated: int = 0
    meetings_skipped: int = 0
    tasks_created: int = 0
    tasks_updated: int = 0
    tasks_skipped: int = 0
    highlights_created: int = 0
    highlights_updated: int = 0
    highlights_skipped: int = 0
    seeded_user_ids: list[uuid.UUID] = field(default_factory=list)
    seeded_task_ids: list[uuid.UUID] = field(default_factory=list)
    seeded_meeting_ids: list[uuid.UUID] = field(default_factory=list)
    seeded_highlight_ids: list[uuid.UUID] = field(default_factory=list)


# ── Account & Seed Manifest ──────────────────────────────────────────────────
DEMO_ACCOUNTS_MANIFEST: Final[list[dict[str, Any]]] = [
    {
        "key": "demo_eng",
        "name": "Alex Chen",
        "first_name": "Alex",
        "last_name": "Chen",
        "email": "alex.chen@demo.meetmind.ai",
        "mobile_number": "+1-555-0101",
        "env_var": "DEMO_PASSWORD_ALEX_CHEN",
        "department": "Engineering & Platform",
        "meetings": [
            {
                "index": 1,
                "title": "Q3 Core Engine Scaling & Vector Partitioning",
                "organization": "MeetMind Engineering",
                "days_offset": -2,
                "time_str": "10:00",
                "transcript": (
                    "Alex Chen: Welcome everyone. Today we're reviewing the scaling bottlenecks in "
                    "our vector ingestion pipeline. We've seen elevated latency during peak hours.\n"
                    "David Ross: I've traced the issue to connection pool leaks in the telemetry worker. "
                    "Under high concurrency, the Redis client doesn't release idle descriptors.\n"
                    "Maya Patel: I recommend adding database query indexing for dashboard stats. PR #142 "
                    "reduces average query execution time from 120ms to 4ms.\n"
                    "Alex Chen: Agreed. Maya, let's merge PR #142 today. David, please patch the connection "
                    "pool leak. I will review the Pinecone retriever memory profiling tomorrow."
                ),
                "participants": [
                    {"index": 1, "name": "Alex Chen", "role": "Staff Platform Architect", "is_current_user": True},
                    {"index": 2, "name": "David Ross", "role": "Senior Infrastructure Engineer", "is_current_user": False},
                    {"index": 3, "name": "Maya Patel", "role": "Backend Systems Engineer", "is_current_user": False},
                ],
            },
            {
                "index": 2,
                "title": "API Gateway & Zero-Trust Architecture",
                "organization": "MeetMind Engineering",
                "days_offset": -6,
                "time_str": "14:00",
                "transcript": (
                    "Alex Chen: Let's discuss our transition to per-user resource isolation and JWT validation.\n"
                    "Ryan Vance: All endpoints now mandate sub-claim validation against user UUIDs. We also need "
                    "to conduct load testing on the authentication rate limiter before deploying to production.\n"
                    "Alex Chen: Good. We also completed deprecation of the unencrypted legacy user consent table "
                    "earlier this week. Next up is upgrading SQLAlchemy drivers across all worker nodes."
                ),
                "participants": [
                    {"index": 1, "name": "Alex Chen", "role": "Staff Platform Architect", "is_current_user": True},
                    {"index": 2, "name": "Ryan Vance", "role": "Security Architect", "is_current_user": False},
                ],
            },
        ],
        "tasks": [
            {
                "index": 1,
                "meeting_index": 1,
                "title": "Patch Redis connection pool leak in telemetry worker",
                "description": "Fix connection descriptor exhaustion during peak concurrent transcription jobs.",
                "priority": TaskPriority.high,
                "scenario": "overdue",  # yesterday 17:00
                "status": TaskStatus.pending,
            },
            {
                "index": 2,
                "meeting_index": 1,
                "title": "Merge PR #142: Database query indexing for dashboard stats",
                "description": "Index user_id, status, and deadline columns to optimize StatCard aggregation queries.",
                "priority": TaskPriority.high,
                "scenario": "today",  # today 23:59:59.999
                "status": TaskStatus.pending,
            },
            {
                "index": 3,
                "meeting_index": 1,
                "title": "Review memory profiling logs for Pinecone retriever",
                "description": "Inspect garbage collection telemetry and vector cache hit ratios under sustained load.",
                "priority": TaskPriority.high,
                "scenario": "tomorrow",  # tomorrow 18:00
                "status": TaskStatus.pending,
            },
            {
                "index": 4,
                "meeting_index": 2,
                "title": "Execute load test on authentication rate limiting",
                "description": "Simulate 5,000 req/sec across API gateway to verify burst thresholds and 429 response formatting.",
                "priority": TaskPriority.medium,
                "scenario": "in_2_days",  # today + 2d 18:00
                "status": TaskStatus.pending,
            },
            {
                "index": 5,
                "meeting_index": 2,
                "title": "Upgrade SQLAlchemy driver across worker nodes",
                "description": "Bump psycopg2-binary and SQLAlchemy connection pool pre-ping timeout configurations.",
                "priority": TaskPriority.low,
                "scenario": "in_14_days",  # today + 14d 17:00
                "status": TaskStatus.pending,
            },
            {
                "index": 6,
                "meeting_index": 2,
                "title": "Deprecate unencrypted legacy user consent table",
                "description": "Verified migration of all active consents to the hashed credentials subsystem.",
                "priority": TaskPriority.medium,
                "scenario": "past_complete",  # today - 4d 12:00
                "status": TaskStatus.complete,
            },
        ],
        "highlights": [
            {
                "index": 1,
                "meeting_index": 1,
                "content": "Agreed to standardize database connection pooling across all background workers.",
            },
            {
                "index": 2,
                "meeting_index": 1,
                "content": "Mandated Argon2id RFC 9106 parameters for all internal microservices.",
            },
            {
                "index": 3,
                "meeting_index": 1,
                "content": "Scheduled production indexing maintenance window for Sunday at 02:00 UTC.",
            },
            {
                "index": 4,
                "meeting_index": 2,
                "content": "Approved migration from raw strings to strict TaskStatus lowercase enums.",
            },
        ],
    },
    {
        "key": "demo_prod",
        "name": "Sarah Lin",
        "first_name": "Sarah",
        "last_name": "Lin",
        "email": "sarah.lin@demo.meetmind.ai",
        "mobile_number": "+1-555-0102",
        "env_var": "DEMO_PASSWORD_SARAH_LIN",
        "department": "Product & UX Design",
        "meetings": [
            {
                "index": 1,
                "title": "Workspace Dashboard UX & StatCard Usability Review",
                "organization": "MeetMind Product",
                "days_offset": -1,
                "time_str": "11:00",
                "transcript": (
                    "Sarah Lin: Welcome team. We are evaluating user testing feedback on the new workspace dashboard.\n"
                    "Liam Wong: The asymmetric 60/40 layout between highlights and upcoming deadlines scored very high. "
                    "Users especially liked that skeleton loaders provide immediate layout stability.\n"
                    "Chloe Bennett: We need to finalize the design tokens for deadline alert color coding. Red for today/tomorrow, "
                    "amber for 2-3 days, and muted grey/green for later dates.\n"
                    "Sarah Lin: Let's approve the deadline alert tokens today. Also make sure completed tasks are filtered "
                    "out of the upcoming deadlines right panel."
                ),
                "participants": [
                    {"index": 1, "name": "Sarah Lin", "role": "Principal Product Manager", "is_current_user": True},
                    {"index": 2, "name": "Liam Wong", "role": "Lead UX Designer", "is_current_user": False},
                    {"index": 3, "name": "Chloe Bennett", "role": "Senior Frontend Engineer", "is_current_user": False},
                ],
            },
            {
                "index": 2,
                "title": "Q4 Feature Roadmap: Transcript Summarization Workflows",
                "organization": "MeetMind Product",
                "days_offset": -5,
                "time_str": "15:30",
                "transcript": (
                    "Sarah Lin: Reviewing our Q4 priorities for meeting summarization workflows.\n"
                    "Marcus Green: Enterprise customers are requesting human-in-the-loop task confirmation before tasks "
                    "are automatically created.\n"
                    "Sarah Lin: Agreed. I'll draft the product brief for human-in-the-loop task confirmation this week, and we'll "
                    "synthesize user interview recordings tomorrow. The contrast palette audit is already complete."
                ),
                "participants": [
                    {"index": 1, "name": "Sarah Lin", "role": "Principal Product Manager", "is_current_user": True},
                    {"index": 2, "name": "Marcus Green", "role": "Group Product Manager", "is_current_user": False},
                ],
            },
        ],
        "tasks": [
            {
                "index": 1,
                "meeting_index": 1,
                "title": "Finalize Figma specifications for mobile sidebar collapse",
                "description": "Align responsive breakpoints and touch targets for mobile viewport under 768px.",
                "priority": TaskPriority.high,
                "scenario": "overdue",
                "status": TaskStatus.pending,
            },
            {
                "index": 2,
                "meeting_index": 1,
                "title": "Approve design tokens for deadline alert color coding",
                "description": "Verify WCAG AAA contrast ratios for high, medium, and low priority deadline badges.",
                "priority": TaskPriority.high,
                "scenario": "today",
                "status": TaskStatus.pending,
            },
            {
                "index": 3,
                "meeting_index": 1,
                "title": "Synthesize user interview recordings for meeting search flow",
                "description": "Categorize qualitative pain points from 12 customer research transcripts.",
                "priority": TaskPriority.high,
                "scenario": "tomorrow",
                "status": TaskStatus.pending,
            },
            {
                "index": 4,
                "meeting_index": 2,
                "title": "Draft product brief for human-in-the-loop task confirmation",
                "description": "Specify confirmation modal states, editability boundaries, and reject workflows.",
                "priority": TaskPriority.medium,
                "scenario": "in_2_days",
                "status": TaskStatus.pending,
            },
            {
                "index": 5,
                "meeting_index": 2,
                "title": "Conduct competitive analysis on automated meeting summaries",
                "description": "Benchmarking extraction accuracy and action item precision across competitor tools.",
                "priority": TaskPriority.low,
                "scenario": "in_14_days",
                "status": TaskStatus.pending,
            },
            {
                "index": 6,
                "meeting_index": 2,
                "title": "Approve color contrast palette for high-priority badges",
                "description": "Verified high-contrast theme meets WCAG 2.1 AA specifications across dark/light mode.",
                "priority": TaskPriority.low,
                "scenario": "past_complete",
                "status": TaskStatus.complete,
            },
        ],
        "highlights": [
            {
                "index": 1,
                "meeting_index": 1,
                "content": "Confirmed 60/40 split between Recent Highlights and Upcoming Deadlines panels.",
            },
            {
                "index": 2,
                "meeting_index": 1,
                "content": "UX interviews showed 92% user satisfaction with instant StatCard skeleton feedback.",
            },
            {
                "index": 3,
                "meeting_index": 1,
                "content": "Decided to suppress completed tasks from the Upcoming Deadlines right-hand panel.",
            },
            {
                "index": 4,
                "meeting_index": 2,
                "content": "Approved design system typography tokens for high-contrast accessibility standards.",
            },
        ],
    },
    {
        "key": "demo_ops",
        "name": "Marcus Vance",
        "first_name": "Marcus",
        "last_name": "Vance",
        "email": "marcus.vance@demo.meetmind.ai",
        "mobile_number": "+1-555-0103",
        "env_var": "DEMO_PASSWORD_MARCUS_VANCE",
        "department": "Customer Operations",
        "meetings": [
            {
                "index": 1,
                "title": "Enterprise Client Onboarding & SLA Incident Review",
                "organization": "MeetMind Operations",
                "days_offset": -2,
                "time_str": "09:30",
                "transcript": (
                    "Marcus Vance: Let's review the onboarding SLA for Acme Corp and recent notification uptime.\n"
                    "Rachel Adams: The webhook delivery timeout issue for Acme Corp was escalated to Tier 3. "
                    "We need to get this resolved immediately.\n"
                    "Tom Miller: Resend delivery rates are healthy at 99.8%. I will audit the sender reputation logs "
                    "today to make sure our SPF and DKIM signatures are clean.\n"
                    "Marcus Vance: Good. I'll publish the updated onboarding checklist tomorrow once Acme confirms "
                    "receipt of their API tokens."
                ),
                "participants": [
                    {"index": 1, "name": "Marcus Vance", "role": "Director of Customer Operations", "is_current_user": True},
                    {"index": 2, "name": "Rachel Adams", "role": "Technical Account Manager", "is_current_user": False},
                    {"index": 3, "name": "Tom Miller", "role": "DevOps Specialist", "is_current_user": False},
                ],
            },
            {
                "index": 2,
                "title": "Support Automation & Webhook Integration Sync",
                "organization": "MeetMind Operations",
                "days_offset": -7,
                "time_str": "16:00",
                "transcript": (
                    "Marcus Vance: Checking in on support ticket volume following the Phase 4 release.\n"
                    "Jenny White: Automated daily health checks have helped catch webhook transient errors early. "
                    "Weekly ticket resolution time dropped by 24%.\n"
                    "Marcus Vance: That's great progress. We already verified Resend onboarding domain DNS records. "
                    "Let's review the support ticket resolution metrics in two days."
                ),
                "participants": [
                    {"index": 1, "name": "Marcus Vance", "role": "Director of Customer Operations", "is_current_user": True},
                    {"index": 2, "name": "Jenny White", "role": "Customer Support Lead", "is_current_user": False},
                ],
            },
        ],
        "tasks": [
            {
                "index": 1,
                "meeting_index": 1,
                "title": "Resolve Tier 3 escalation for Acme Corp webhook delivery",
                "description": "Investigate mutual TLS handshake dropouts on enterprise receiving endpoint.",
                "priority": TaskPriority.high,
                "scenario": "overdue",
                "status": TaskStatus.pending,
            },
            {
                "index": 2,
                "meeting_index": 1,
                "title": "Audit Resend notification sender reputation logs",
                "description": "Inspect bounce rates, complaint metrics, and SPF/DKIM verification statuses.",
                "priority": TaskPriority.high,
                "scenario": "today",
                "status": TaskStatus.pending,
            },
            {
                "index": 3,
                "meeting_index": 1,
                "title": "Publish updated onboarding checklist for pilot enterprise users",
                "description": "Incorporate SSO integration steps and webhook endpoint verification guidelines.",
                "priority": TaskPriority.high,
                "scenario": "tomorrow",
                "status": TaskStatus.pending,
            },
            {
                "index": 4,
                "meeting_index": 2,
                "title": "Review weekly customer support ticket resolution metrics",
                "description": "Analyze first-response time and mean time to resolution across Phase 4 cohorts.",
                "priority": TaskPriority.medium,
                "scenario": "in_2_days",
                "status": TaskStatus.pending,
            },
            {
                "index": 5,
                "meeting_index": 2,
                "title": "Plan quarterly infrastructure review with cloud provider TAM",
                "description": "Schedule reserved instance utilization audit and multi-region failover dry run.",
                "priority": TaskPriority.low,
                "scenario": "in_14_days",
                "status": TaskStatus.pending,
            },
            {
                "index": 6,
                "meeting_index": 2,
                "title": "Verify Resend onboarding domain DNS DKIM/SPF records",
                "description": "Confirmed CNAME and TXT validation records are active and resolving correctly.",
                "priority": TaskPriority.high,
                "scenario": "past_complete",
                "status": TaskStatus.complete,
            },
        ],
        "highlights": [
            {
                "index": 1,
                "meeting_index": 1,
                "content": "Established a 15-minute SLA target for enterprise pipeline failure alerts.",
            },
            {
                "index": 2,
                "meeting_index": 1,
                "content": "Confirmed 99.8% on-time email notification delivery rate over the past 30 days.",
            },
            {
                "index": 3,
                "meeting_index": 1,
                "content": "Adopted automated daily health checks for background notification scheduler.",
            },
            {
                "index": 4,
                "meeting_index": 2,
                "content": "Acme Corp pilot onboarding completed with zero data access discrepancies.",
            },
        ],
    },
    {
        "key": "demo_hr",
        "name": "Elena Rostova",
        "first_name": "Elena",
        "last_name": "Rostova",
        "email": "elena.rostova@demo.meetmind.ai",
        "mobile_number": "+1-555-0104",
        "env_var": "DEMO_PASSWORD_ELENA_ROSTOVA",
        "department": "People & Talent",
        "meetings": [
            {
                "index": 1,
                "title": "Q4 Engineering Headcount & Strategic Talent Review",
                "organization": "MeetMind People",
                "days_offset": -1,
                "time_str": "13:00",
                "transcript": (
                    "Elena Rostova: Thank you for joining our Q4 talent review.\n"
                    "Nina Simone: We need 4 senior backend and AI roles opened for our Phase 5 real-time audio pipeline.\n"
                    "Eric Gomez: The candidate for Staff Frontend Engineer completed their final loop with flying colors. "
                    "We need to send the offer letter today before competing offers close.\n"
                    "Elena Rostova: I'll prepare and send that offer letter this afternoon. Eric, please schedule executive "
                    "debriefs for the AI Researcher finalists tomorrow."
                ),
                "participants": [
                    {"index": 1, "name": "Elena Rostova", "role": "VP of People & Culture", "is_current_user": True},
                    {"index": 2, "name": "Nina Simone", "role": "VP of Engineering", "is_current_user": False},
                    {"index": 3, "name": "Eric Gomez", "role": "Lead Technical Recruiter", "is_current_user": False},
                ],
            },
            {
                "index": 2,
                "title": "Annual Leadership Offsite & Culture Planning",
                "organization": "MeetMind People",
                "days_offset": -4,
                "time_str": "10:30",
                "transcript": (
                    "Elena Rostova: Today we are reviewing logistics and agenda for our annual leadership offsite.\n"
                    "Arthur Pendelton: Board members have confirmed attendance. The executive committee approved the updated "
                    "remote equipment stipend policy earlier this week.\n"
                    "Elena Rostova: Great. We will finalize the offsite venue contract in two days and schedule the company-wide "
                    "culture survey rollout for mid-quarter."
                ),
                "participants": [
                    {"index": 1, "name": "Elena Rostova", "role": "VP of People & Culture", "is_current_user": True},
                    {"index": 2, "name": "Arthur Pendelton", "role": "Board Liaison", "is_current_user": False},
                ],
            },
        ],
        "tasks": [
            {
                "index": 1,
                "meeting_index": 1,
                "title": "Submit revised compensation benchmarking survey",
                "description": "Incorporate tech sector salary band adjustments for engineering and product roles.",
                "priority": TaskPriority.high,
                "scenario": "overdue",
                "status": TaskStatus.pending,
            },
            {
                "index": 2,
                "meeting_index": 1,
                "title": "Send offer letter to Staff Frontend Engineer candidate",
                "description": "Issue signed formal offer with equity schedule and standard IP agreement.",
                "priority": TaskPriority.high,
                "scenario": "today",
                "status": TaskStatus.pending,
            },
            {
                "index": 3,
                "meeting_index": 1,
                "title": "Schedule executive debriefs for Senior AI Researcher finalists",
                "description": "Coordinate 30-minute alignment calls with CTO and lead research architects.",
                "priority": TaskPriority.high,
                "scenario": "tomorrow",
                "status": TaskStatus.pending,
            },
            {
                "index": 4,
                "meeting_index": 2,
                "title": "Finalize venue contract for November leadership offsite",
                "description": "Review audiovisual facilities, guest accommodations, and cancellation policies.",
                "priority": TaskPriority.medium,
                "scenario": "in_2_days",
                "status": TaskStatus.pending,
            },
            {
                "index": 5,
                "meeting_index": 2,
                "title": "Roll out annual company-wide culture and engagement survey",
                "description": "Distribute anonymous feedback questionnaire and configure executive analytics.",
                "priority": TaskPriority.low,
                "scenario": "in_14_days",
                "status": TaskStatus.pending,
            },
            {
                "index": 6,
                "meeting_index": 2,
                "title": "Approve revised workplace security and device policy",
                "description": "Confirmed hardware disk encryption and 2FA authentication requirements.",
                "priority": TaskPriority.medium,
                "scenario": "past_complete",
                "status": TaskStatus.complete,
            },
        ],
        "highlights": [
            {
                "index": 1,
                "meeting_index": 1,
                "content": "Approved 4 new engineering requisitions for Phase 5 real-time audio pipeline.",
            },
            {
                "index": 2,
                "meeting_index": 1,
                "content": "Offsite location finalized for November with full team attendance.",
            },
            {
                "index": 3,
                "meeting_index": 1,
                "content": "Updated remote worker equipment stipend policy approved by executive committee.",
            },
            {
                "index": 4,
                "meeting_index": 2,
                "content": "Completed third-quarter diversity and inclusion compensation equity audit.",
            },
        ],
    },
]


# ── Core Seeding Implementation ──────────────────────────────────────────────
def seed_demo_data(
    db: Session,
    *,
    timezone_name: str | None = None,
    reset_passwords: bool = False,
    reset_task_status: bool = False,
    reseed_demo_data: bool = False,
) -> SeederReport:
    """
    Executes deterministic, idempotent demo data seeding.

    Args:
        db: Active SQLAlchemy database session.
        timezone_name: Optional explicit timezone string (overrides DEMO_DATA_TIMEZONE).
        reset_passwords: If True, forces re-hashing of passwords from env vars.
        reset_task_status: If True, restores task statuses to baseline (1-5 pending, 6 complete).
        reseed_demo_data: If True, updates titles/transcripts/highlights in place.

    Returns:
        SeederReport: Summary of created, updated, and skipped entities.
    """
    target_tz = resolve_seeder_timezone(timezone_name)
    target_now = datetime.now(target_tz)
    target_today = target_now.date()

    report = SeederReport()

    # Pre-validate passwords for initial creation or reset-passwords mode
    env_passwords: dict[str, str] = {}
    for account_data in DEMO_ACCOUNTS_MANIFEST:
        env_var = account_data["env_var"]
        pwd = os.getenv(env_var)
        if pwd:
            pwd = pwd.strip()
            # Strip enclosing quotes if any
            if (pwd.startswith('"') and pwd.endswith('"')) or (pwd.startswith("'") and pwd.endswith("'")):
                pwd = pwd[1:-1]
        env_passwords[env_var] = pwd or ""

    for account_data in DEMO_ACCOUNTS_MANIFEST:
        account_key = account_data["key"]
        demo_user_id = get_demo_user_id(account_key)
        demo_email = account_data["email"]
        env_var = account_data["env_var"]
        raw_password = env_passwords[env_var]

        report.seeded_user_ids.append(demo_user_id)

        # ── 1. Defensive Collision Checks ──────────────────────────────────
        # Check if email is held by an unrelated non-deterministic user ID
        existing_by_email = db.query(User).filter(User.email == demo_email).first()
        if existing_by_email and existing_by_email.id != demo_user_id:
            raise RuntimeError(
                f"Safety Collision Guard: Email '{demo_email}' is already registered to user ID "
                f"'{existing_by_email.id}', which does not match expected deterministic demo UUID "
                f"'{demo_user_id}'. Seeding aborted to protect existing user data."
            )

        # Check if deterministic demo UUID is held by a mismatched email
        existing_by_id = db.query(User).filter(User.id == demo_user_id).first()
        if existing_by_id and existing_by_id.email != demo_email:
            raise RuntimeError(
                f"Safety Collision Guard: Demo UUID '{demo_user_id}' already has registered email "
                f"'{existing_by_id.email}', which does not match expected demo email '{demo_email}'. "
                f"Seeding aborted."
            )

        # ── 2. Create or Identify User ─────────────────────────────────────
        user = existing_by_id or existing_by_email
        if not user:
            # Requires valid environment password for initial creation
            if not raw_password:
                raise ValueError(
                    f"Missing required environment variable '{env_var}' for demo account '{demo_email}'. "
                    f"Account creation halted. No fallback or default password will be assigned."
                )

            is_valid, error_msg = validate_password_complexity(raw_password)
            if not is_valid:
                raise ValueError(
                    f"Password for demo account '{demo_email}' from '{env_var}' fails complexity rules: {error_msg}"
                )

            user = User(
                id=demo_user_id,
                name=account_data["name"],
                first_name=account_data["first_name"],
                last_name=account_data["last_name"],
                mobile_number=account_data["mobile_number"],
                email=demo_email,
            )
            db.add(user)
            db.flush()  # Ensure user is written before credentials

            # Create UserCredentials
            pwd_hash = hash_password(raw_password)
            credentials = UserCredentials(
                user_id=demo_user_id,
                password_hash=pwd_hash,
            )
            db.add(credentials)
            report.users_created += 1
            logger.info(f"Created demo account: {demo_email} (UUID: {demo_user_id})")
        else:
            # User already exists
            report.users_skipped += 1
            if reseed_demo_data:
                user.name = account_data["name"]
                user.first_name = account_data["first_name"]
                user.last_name = account_data["last_name"]
                user.mobile_number = account_data["mobile_number"]
                report.users_updated += 1

            # Handle password reset if explicitly requested
            if reset_passwords:
                if not raw_password:
                    raise ValueError(
                        f"Cannot reset password for '{demo_email}': environment variable '{env_var}' is empty or unset."
                    )
                is_valid, error_msg = validate_password_complexity(raw_password)
                if not is_valid:
                    raise ValueError(
                        f"Cannot reset password for '{demo_email}': password in '{env_var}' fails complexity: {error_msg}"
                    )
                creds = db.query(UserCredentials).filter(UserCredentials.user_id == demo_user_id).first()
                new_hash = hash_password(raw_password)
                if creds:
                    creds.password_hash = new_hash
                else:
                    creds = UserCredentials(user_id=demo_user_id, password_hash=new_hash)
                    db.add(creds)
                report.passwords_reset += 1
                logger.info(f"Reset password for demo account: {demo_email}")

        # ── 3. Meetings & Participants ────────────────────────────────────
        meeting_id_map: dict[int, uuid.UUID] = {}
        for meeting_data in account_data["meetings"]:
            m_idx = meeting_data["index"]
            meeting_id = get_demo_meeting_id(account_key, m_idx)
            meeting_id_map[m_idx] = meeting_id
            report.seeded_meeting_ids.append(meeting_id)

            m_date = target_today + timedelta(days=meeting_data["days_offset"])

            existing_meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
            if not existing_meeting:
                meeting = Meeting(
                    id=meeting_id,
                    user_id=demo_user_id,
                    title=meeting_data["title"],
                    organization=meeting_data["organization"],
                    meeting_date=m_date,
                    meeting_time=meeting_data["time_str"],
                    raw_transcript=meeting_data["transcript"],
                    input_format="text",
                    pinecone_namespace=f"demo-{account_key}-m{m_idx}",
                )
                db.add(meeting)
                db.flush()
                report.meetings_created += 1
            else:
                if reseed_demo_data:
                    existing_meeting.title = meeting_data["title"]
                    existing_meeting.organization = meeting_data["organization"]
                    existing_meeting.meeting_date = m_date
                    existing_meeting.meeting_time = meeting_data["time_str"]
                    existing_meeting.raw_transcript = meeting_data["transcript"]
                    report.meetings_updated += 1
                else:
                    report.meetings_skipped += 1

            # Participants
            for p_data in meeting_data["participants"]:
                p_idx = p_data["index"]
                p_id = get_demo_participant_id(account_key, m_idx, p_idx)
                existing_p = db.query(MeetingParticipant).filter(MeetingParticipant.id == p_id).first()
                if not existing_p:
                    participant = MeetingParticipant(
                        id=p_id,
                        meeting_id=meeting_id,
                        name=p_data["name"],
                        role=p_data["role"],
                        is_current_user=p_data["is_current_user"],
                    )
                    db.add(participant)
                elif reseed_demo_data:
                    existing_p.name = p_data["name"]
                    existing_p.role = p_data["role"]
                    existing_p.is_current_user = p_data["is_current_user"]

        # ── 4. Tasks ──────────────────────────────────────────────────────
        for task_data in account_data["tasks"]:
            t_idx = task_data["index"]
            task_id = get_demo_task_id(account_key, t_idx)
            report.seeded_task_ids.append(task_id)

            parent_meeting_id = meeting_id_map[task_data["meeting_index"]]
            scenario = task_data["scenario"]

            # Compute relative deadline anchored to target timezone
            if scenario == "overdue":
                local_dt = datetime.combine(
                    target_today - timedelta(days=1), time(17, 0, 0), tzinfo=target_tz
                )
                deadline_utc = local_dt.astimezone(timezone.utc)
            elif scenario == "today":
                deadline_utc = compute_due_today_deadline(target_now)
            elif scenario == "tomorrow":
                local_dt = datetime.combine(
                    target_today + timedelta(days=1), time(18, 0, 0), tzinfo=target_tz
                )
                deadline_utc = local_dt.astimezone(timezone.utc)
            elif scenario == "in_2_days":
                local_dt = datetime.combine(
                    target_today + timedelta(days=2), time(18, 0, 0), tzinfo=target_tz
                )
                deadline_utc = local_dt.astimezone(timezone.utc)
            elif scenario == "in_14_days":
                local_dt = datetime.combine(
                    target_today + timedelta(days=14), time(17, 0, 0), tzinfo=target_tz
                )
                deadline_utc = local_dt.astimezone(timezone.utc)
            elif scenario == "past_complete":
                local_dt = datetime.combine(
                    target_today - timedelta(days=4), time(12, 0, 0), tzinfo=target_tz
                )
                deadline_utc = local_dt.astimezone(timezone.utc)
            else:
                deadline_utc = None

            existing_task = db.query(Task).filter(Task.id == task_id).first()
            if not existing_task:
                task = Task(
                    id=task_id,
                    meeting_id=parent_meeting_id,
                    user_id=demo_user_id,
                    title=task_data["title"],
                    description=task_data["description"],
                    priority=task_data["priority"],
                    deadline=deadline_utc,
                    status=task_data["status"],
                    alert_sent=False,
                )
                db.add(task)
                report.tasks_created += 1
            else:
                task_modified = False
                if reset_task_status and existing_task.status != task_data["status"]:
                    existing_task.status = task_data["status"]
                    task_modified = True
                if reseed_demo_data:
                    existing_task.title = task_data["title"]
                    existing_task.description = task_data["description"]
                    existing_task.priority = task_data["priority"]
                    existing_task.deadline = deadline_utc
                    task_modified = True
                if task_modified:
                    report.tasks_updated += 1
                else:
                    report.tasks_skipped += 1

        # ── 5. Highlights ─────────────────────────────────────────────────
        for h_data in account_data["highlights"]:
            h_idx = h_data["index"]
            h_id = get_demo_highlight_id(account_key, h_idx)
            report.seeded_highlight_ids.append(h_id)

            parent_meeting_id = meeting_id_map[h_data["meeting_index"]]

            existing_highlight = db.query(Highlight).filter(Highlight.id == h_id).first()
            if not existing_highlight:
                highlight = Highlight(
                    id=h_id,
                    meeting_id=parent_meeting_id,
                    user_id=demo_user_id,
                    content=h_data["content"],
                )
                db.add(highlight)
                report.highlights_created += 1
            else:
                if reseed_demo_data:
                    existing_highlight.content = h_data["content"]
                    report.highlights_updated += 1
                else:
                    report.highlights_skipped += 1

    return report


def main() -> None:
    """CLI entrypoint for demo data seeding."""
    parser = argparse.ArgumentParser(
        description="MeetMind AI — Batch 4.9: Four Demo Accounts & Realistic Test Data Seeder."
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default=None,
        help="Target IANA timezone for relative deadlines (e.g., 'Asia/Kolkata', 'UTC').",
    )
    parser.add_argument(
        "--reset-passwords",
        action="store_true",
        default=False,
        help="Reset demo account password hashes using configured environment variables.",
    )
    parser.add_argument(
        "--reset-task-status",
        action="store_true",
        default=False,
        help="Reset task statuses to baseline (Tasks 1-5 pending, Task 6 complete) for demo tasks only.",
    )
    parser.add_argument(
        "--reseed-demo-data",
        action="store_true",
        default=False,
        help="Refresh deadlines, titles, descriptions, transcripts, and highlights in place without touching user-created data.",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("MeetMind AI — Batch 4.9: Deterministic Demo Data Seeder")
    print("=" * 70)

    try:
        resolved_tz = resolve_seeder_timezone(args.timezone)
        print(f"Target Timezone: {resolved_tz.key}")
        print(f"Current Target Time: {datetime.now(resolved_tz).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Reset Passwords: {args.reset_passwords}")
        print(f"Reset Task Statuses: {args.reset_task_status}")
        print(f"Reseed Demo Data: {args.reseed_demo_data}")
        print("-" * 70)

        db: Session = SessionLocal()
        try:
            with db.begin():
                report = seed_demo_data(
                    db,
                    timezone_name=args.timezone,
                    reset_passwords=args.reset_passwords,
                    reset_task_status=args.reset_task_status,
                    reseed_demo_data=args.reseed_demo_data,
                )

            print("Seeding Execution Completed Successfully:")
            print(f"  Users:       {report.users_created} created, {report.users_updated} updated, {report.users_skipped} existing")
            if args.reset_passwords:
                print(f"  Passwords:   {report.passwords_reset} reset")
            print(f"  Meetings:    {report.meetings_created} created, {report.meetings_updated} updated, {report.meetings_skipped} existing")
            print(f"  Tasks:       {report.tasks_created} created, {report.tasks_updated} updated, {report.tasks_skipped} existing")
            print(f"  Highlights:  {report.highlights_created} created, {report.highlights_updated} updated, {report.highlights_skipped} existing")
            print("=" * 70)
        finally:
            db.close()

    except Exception as exc:
        print(f"\n[ERROR] Seeding failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
