"""
Comprehensive test suite for Batch 4.9: Deterministic Demo Data Seeding System.

Covers:
A. Account Creation & Password Hashing
B. Idempotency & Unrelated Data Preservation
C. Data Integrity (2 meetings, 6 tasks, 4 highlights per account)
D. Authentication via API (all 4 demo accounts)
E. Cross-User Isolation & Ownership Enforcement
F. Dashboard Metrics Verification (State 1 Baseline)
G. Failure Handling & Defensive Collision Guards
H. Seeder CLI Options (--reset-passwords, --reset-task-status, --reseed-demo-data)
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import zoneinfo

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.security import verify_password
from app.db.base import Base
from app.db.models.highlight import Highlight
from app.db.models.meeting import Meeting
from app.db.models.meeting_participant import MeetingParticipant
from app.db.models.task import Task, TaskPriority, TaskStatus
from app.db.models.user import User
from app.db.models.user_credentials import UserCredentials
from app.db.seed_demo_data import (
    DEMO_ACCOUNTS_MANIFEST,
    SEED_NAMESPACE,
    compute_due_today_deadline,
    get_demo_highlight_id,
    get_demo_meeting_id,
    get_demo_participant_id,
    get_demo_task_id,
    get_demo_user_id,
    resolve_seeder_timezone,
    seed_demo_data,
)
from app.db.session import get_db
from app.main import app

# Standard valid test passwords for the 4 demo accounts
TEST_PASSWORDS = {
    "DEMO_PASSWORD_ALEX_CHEN": "AlexPass#2026",
    "DEMO_PASSWORD_SARAH_LIN": "SarahPass#2026",
    "DEMO_PASSWORD_MARCUS_VANCE": "MarcusPass#26",
    "DEMO_PASSWORD_ELENA_ROSTOVA": "ElenaPass#2026",
    "DEMO_DATA_TIMEZONE": "UTC",
}


class BaseSeedDemoDataTestCase(unittest.TestCase):
    """Sets up an in-memory SQLite database and isolated FastAPI TestClient."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db: Session = self.SessionLocal()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        # Apply mock environment variables for test passwords
        self.env_patcher = patch.dict(os.environ, TEST_PASSWORDS, clear=False)
        self.env_patcher.start()

    def tearDown(self) -> None:
        self.env_patcher.stop()
        app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(self.engine)


class TestDemoAccountCreation(BaseSeedDemoDataTestCase):
    """Tests A: Account creation, determinism, and credential security."""

    def test_all_four_accounts_created_with_deterministic_uuids(self) -> None:
        report = seed_demo_data(self.db)
        self.db.commit()

        self.assertEqual(report.users_created, 4)
        users = self.db.query(User).all()
        self.assertEqual(len(users), 4)

        for account in DEMO_ACCOUNTS_MANIFEST:
            expected_uuid = get_demo_user_id(account["key"])
            user = self.db.query(User).filter(User.id == expected_uuid).first()
            self.assertIsNotNone(user, f"User {account['email']} should exist with UUID {expected_uuid}")
            self.assertEqual(user.email, account["email"])
            self.assertEqual(user.name, account["name"])
            self.assertEqual(user.first_name, account["first_name"])
            self.assertEqual(user.last_name, account["last_name"])
            self.assertEqual(user.mobile_number, account["mobile_number"])

            # Verify credentials and Argon2id hash
            creds = self.db.query(UserCredentials).filter(UserCredentials.user_id == expected_uuid).first()
            self.assertIsNotNone(creds)
            self.assertTrue(creds.password_hash.startswith("$argon2id$"))
            raw_pwd = TEST_PASSWORDS[account["env_var"]]
            self.assertTrue(verify_password(raw_pwd, creds.password_hash))


class TestIdempotencyAndPreservation(BaseSeedDemoDataTestCase):
    """Tests B: Idempotency, password preservation, and user-created data protection."""

    def test_seeding_is_idempotent(self) -> None:
        report1 = seed_demo_data(self.db)
        self.db.commit()
        self.assertEqual(report1.users_created, 4)
        self.assertEqual(report1.meetings_created, 8)
        self.assertEqual(report1.tasks_created, 24)
        self.assertEqual(report1.highlights_created, 16)

        # Run seeder a second time
        report2 = seed_demo_data(self.db)
        self.db.commit()
        self.assertEqual(report2.users_created, 0)
        self.assertEqual(report2.users_updated, 0)
        self.assertEqual(report2.users_skipped, 4)
        self.assertEqual(report2.meetings_created, 0)
        self.assertEqual(report2.meetings_updated, 0)
        self.assertEqual(report2.meetings_skipped, 8)
        self.assertEqual(report2.tasks_created, 0)
        self.assertEqual(report2.tasks_updated, 0)
        self.assertEqual(report2.tasks_skipped, 24)
        self.assertEqual(report2.highlights_created, 0)
        self.assertEqual(report2.highlights_updated, 0)
        self.assertEqual(report2.highlights_skipped, 16)

        # Confirm total counts in database
        self.assertEqual(self.db.query(User).count(), 4)
        self.assertEqual(self.db.query(Meeting).count(), 8)
        self.assertEqual(self.db.query(Task).count(), 24)
        self.assertEqual(self.db.query(Highlight).count(), 16)

    def test_user_modified_task_deadlines_and_fields_preserved_on_normal_rerun(self) -> None:
        seed_demo_data(self.db)
        self.db.commit()

        # User modifies task 1: custom deadline, custom title, custom description, custom status
        t1_id = get_demo_task_id("demo_eng", 1)
        task_1 = self.db.query(Task).filter(Task.id == t1_id).first()
        custom_deadline = datetime(2027, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        task_1.deadline = custom_deadline
        task_1.title = "User Custom Task Title"
        task_1.description = "User custom description notes"
        task_1.status = TaskStatus.complete
        self.db.commit()

        # Run normal seeder (no flags)
        report = seed_demo_data(self.db)
        self.db.commit()

        self.assertEqual(report.tasks_created, 0)
        self.assertEqual(report.tasks_updated, 0)
        self.assertEqual(report.tasks_skipped, 24)

        # Re-fetch task 1 and verify custom modifications were NOT overwritten
        task_1_refetched = self.db.query(Task).filter(Task.id == t1_id).first()
        # In SQLite datetime comparison handles offset-naive or tz-aware
        self.assertEqual(task_1_refetched.title, "User Custom Task Title")
        self.assertEqual(task_1_refetched.description, "User custom description notes")
        self.assertEqual(task_1_refetched.status, TaskStatus.complete)
        self.assertEqual(
            task_1_refetched.deadline.replace(tzinfo=timezone.utc),
            custom_deadline,
        )

    def test_reseed_demo_data_refreshes_deadlines_and_content_without_resetting_status(self) -> None:
        seed_demo_data(self.db)
        self.db.commit()

        t1_id = get_demo_task_id("demo_eng", 1)
        task_1 = self.db.query(Task).filter(Task.id == t1_id).first()
        custom_deadline = datetime(2027, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        task_1.deadline = custom_deadline
        task_1.title = "User Custom Task Title"
        task_1.status = TaskStatus.complete
        self.db.commit()

        # Reseed demo data (refreshes content and deadlines, preserves status unless --reset-task-status is set)
        report = seed_demo_data(self.db, reseed_demo_data=True)
        self.db.commit()

        self.assertEqual(report.tasks_updated, 24)

        task_1_refetched = self.db.query(Task).filter(Task.id == t1_id).first()
        # Title and deadline refreshed back to manifest
        self.assertNotEqual(task_1_refetched.title, "User Custom Task Title")
        self.assertNotEqual(
            task_1_refetched.deadline.replace(tzinfo=timezone.utc),
            custom_deadline,
        )
        # Status preserved because reset_task_status was False
        self.assertEqual(task_1_refetched.status, TaskStatus.complete)

    def test_existing_password_hashes_preserved_on_rerun(self) -> None:
        seed_demo_data(self.db)
        self.db.commit()

        alex_id = get_demo_user_id("demo_eng")
        creds_before = self.db.query(UserCredentials).filter(UserCredentials.user_id == alex_id).first()
        original_hash = creds_before.password_hash

        # Run again without --reset-passwords
        seed_demo_data(self.db)
        self.db.commit()

        creds_after = self.db.query(UserCredentials).filter(UserCredentials.user_id == alex_id).first()
        self.assertEqual(creds_after.password_hash, original_hash)

    def test_evaluator_created_records_preserved(self) -> None:
        seed_demo_data(self.db)
        self.db.commit()

        alex_id = get_demo_user_id("demo_eng")
        custom_meeting_id = uuid.uuid4()
        custom_meeting = Meeting(
            id=custom_meeting_id,
            user_id=alex_id,
            title="Custom Evaluator Meeting",
            organization="Custom Org",
            meeting_date=datetime.now(timezone.utc).date(),
            meeting_time="11:00",
            raw_transcript="Evaluator transcript.",
            input_format="text",
        )
        self.db.add(custom_meeting)

        custom_task_id = uuid.uuid4()
        custom_task = Task(
            id=custom_task_id,
            meeting_id=custom_meeting_id,
            user_id=alex_id,
            title="Custom Evaluator Task",
            description="Custom description",
            priority=TaskPriority.medium,
            status=TaskStatus.pending,
        )
        self.db.add(custom_task)
        self.db.commit()

        # Rerun seeder with reset options
        seed_demo_data(self.db, reset_task_status=True, reseed_demo_data=True)
        self.db.commit()

        # Custom meeting and task must be 100% intact
        self.assertIsNotNone(self.db.query(Meeting).filter(Meeting.id == custom_meeting_id).first())
        self.assertIsNotNone(self.db.query(Task).filter(Task.id == custom_task_id).first())
        self.assertEqual(self.db.query(Meeting).count(), 9)  # 8 demo + 1 custom
        self.assertEqual(self.db.query(Task).count(), 25)     # 24 demo + 1 custom


class TestDataIntegrityAndDeadlines(BaseSeedDemoDataTestCase):
    """Tests C: Entity distribution, deadline scenarios, and statuses."""

    def test_per_account_data_distribution(self) -> None:
        seed_demo_data(self.db)
        self.db.commit()

        for account in DEMO_ACCOUNTS_MANIFEST:
            user_id = get_demo_user_id(account["key"])
            meetings = self.db.query(Meeting).filter(Meeting.user_id == user_id).all()
            tasks = self.db.query(Task).filter(Task.user_id == user_id).all()
            highlights = self.db.query(Highlight).filter(Highlight.user_id == user_id).all()

            self.assertEqual(len(meetings), 2, f"{account['name']} should have 2 meetings")
            self.assertEqual(len(tasks), 6, f"{account['name']} should have 6 tasks")
            self.assertEqual(len(highlights), 4, f"{account['name']} should have 4 highlights")

            # Validate task statuses
            pending_tasks = [t for t in tasks if t.status == TaskStatus.pending]
            complete_tasks = [t for t in tasks if t.status == TaskStatus.complete]
            self.assertEqual(len(pending_tasks), 5)
            self.assertEqual(len(complete_tasks), 1)

            # Check task 6 is complete
            task_6_id = get_demo_task_id(account["key"], 6)
            task_6 = self.db.query(Task).filter(Task.id == task_6_id).first()
            self.assertEqual(task_6.status, TaskStatus.complete)

    def test_millisecond_deadline_precision(self) -> None:
        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        target_now = datetime(2026, 9, 26, 11, 30, 0, tzinfo=tz)
        due_today_utc = compute_due_today_deadline(target_now)

        # Microsecond component must be exactly 999000
        self.assertEqual(due_today_utc.microsecond, 999000)
        # Convert back to target_tz; must be 23:59:59.999000
        target_dt = due_today_utc.astimezone(tz)
        self.assertEqual(target_dt.hour, 23)
        self.assertEqual(target_dt.minute, 59)
        self.assertEqual(target_dt.second, 59)
        self.assertEqual(target_dt.microsecond, 999000)


class TestAuthenticationViaApi(BaseSeedDemoDataTestCase):
    """Tests D: Authentication and JWT issuance for all 4 demo accounts."""

    def test_all_demo_accounts_can_login_via_api(self) -> None:
        seed_demo_data(self.db)
        self.db.commit()

        for account in DEMO_ACCOUNTS_MANIFEST:
            email = account["email"]
            password = TEST_PASSWORDS[account["env_var"]]
            expected_uuid = str(get_demo_user_id(account["key"]))

            response = self.client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            self.assertEqual(
                response.status_code,
                200,
                f"Login failed for {email}: {response.text}",
            )
            payload = response.json()
            self.assertIn("access_token", payload)
            self.assertEqual(payload["token_type"], "bearer")
            self.assertEqual(payload["user"]["id"], expected_uuid)
            self.assertEqual(payload["user"]["email"], email)


class TestCrossUserDataIsolation(BaseSeedDemoDataTestCase):
    """Tests E: Strict cross-user data isolation for demo accounts."""

    def test_cross_user_isolation(self) -> None:
        seed_demo_data(self.db)
        self.db.commit()

        # Login as Alex Chen (Account 1)
        login_alex = self.client.post(
            "/api/v1/auth/login",
            json={"email": "alex.chen@demo.meetmind.ai", "password": TEST_PASSWORDS["DEMO_PASSWORD_ALEX_CHEN"]},
        )
        alex_token = login_alex.json()["access_token"]
        alex_headers = {"Authorization": f"Bearer {alex_token}"}
        alex_id = str(get_demo_user_id("demo_eng"))

        # Verify Alex lists only his own 2 meetings
        res_meetings = self.client.get("/api/v1/meetings/", headers=alex_headers)
        self.assertEqual(res_meetings.status_code, 200)
        self.assertEqual(len(res_meetings.json()), 2)
        for m in res_meetings.json():
            self.assertEqual(m["user_id"], alex_id)

        # Verify Alex lists only his own 6 tasks
        res_tasks = self.client.get("/api/v1/tasks/", headers=alex_headers)
        self.assertEqual(res_tasks.status_code, 200)
        self.assertEqual(len(res_tasks.json()), 6)
        for t in res_tasks.json():
            self.assertEqual(t["user_id"], alex_id)

        # Attempt to access Sarah Lin's meeting detail as Alex Chen
        sarah_m1_id = str(get_demo_meeting_id("demo_prod", 1))
        res_cross = self.client.get(f"/api/v1/meetings/{sarah_m1_id}", headers=alex_headers)
        self.assertEqual(res_cross.status_code, 404)


class TestDashboardMetricsBaseline(BaseSeedDemoDataTestCase):
    """Tests F: Baseline dashboard metrics reconciliation (State 1)."""

    def test_baseline_dashboard_metrics_state_1(self) -> None:
        seed_demo_data(self.db)
        self.db.commit()

        # Authenticate as Alex Chen
        login_res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "alex.chen@demo.meetmind.ai", "password": TEST_PASSWORDS["DEMO_PASSWORD_ALEX_CHEN"]},
        )
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        # Fetch meetings, tasks, highlights
        meetings = self.client.get("/api/v1/meetings/", headers=headers).json()
        tasks = self.client.get("/api/v1/tasks/", headers=headers).json()
        raw_highlights = self.client.get("/api/v1/highlights/", headers=headers).json()
        highlights_list = raw_highlights if isinstance(raw_highlights, list) else raw_highlights.get("highlights", [])

        self.assertEqual(len(meetings), 2)
        self.assertEqual(len(tasks), 6)
        self.assertEqual(len(highlights_list), 4)

        # Simulate client-side useDashboardData accumulator under State 1
        now_utc = datetime.now(timezone.utc)
        active_count = 0
        completed_count = 0
        expired_count = 0

        for t in tasks:
            if t["status"] == "complete":
                completed_count += 1
            elif t["status"] == "pending":
                # Parse deadline
                dl = datetime.fromisoformat(t["deadline"].replace("Z", "+00:00"))
                if dl < now_utc:
                    expired_count += 1
                else:
                    active_count += 1

        self.assertEqual(active_count, 4, "State 1 baseline: 4 active tasks")
        self.assertEqual(expired_count, 1, "State 1 baseline: 1 overdue task")
        self.assertEqual(completed_count, 1, "State 1 baseline: 1 completed task")
        self.assertEqual(active_count + expired_count + completed_count, 6)


class TestFailureHandlingAndGuards(BaseSeedDemoDataTestCase):
    """Tests G: Missing env vars, invalid passwords, collision guards, invalid timezone."""

    def test_missing_environment_variable_aborts_without_fallback(self) -> None:
        # Clear one password
        with patch.dict(os.environ, {"DEMO_PASSWORD_ALEX_CHEN": ""}):
            with self.assertRaises(ValueError) as ctx:
                seed_demo_data(self.db)
            self.assertIn("Missing required environment variable", str(ctx.exception))
            # Zero users created
            self.assertEqual(self.db.query(User).count(), 0)

    def test_invalid_password_complexity_aborts(self) -> None:
        with patch.dict(os.environ, {"DEMO_PASSWORD_ALEX_CHEN": "short"}):
            with self.assertRaises(ValueError) as ctx:
                seed_demo_data(self.db)
            self.assertIn("fails complexity rules", str(ctx.exception))
            self.assertEqual(self.db.query(User).count(), 0)

    def test_collision_guard_existing_email_different_uuid(self) -> None:
        # Pre-insert an unrelated user with Alex's email but a random UUID
        unrelated_uuid = uuid.uuid4()
        unrelated_user = User(
            id=unrelated_uuid,
            name="Impostor Alex",
            email="alex.chen@demo.meetmind.ai",
        )
        self.db.add(unrelated_user)
        self.db.commit()

        with self.assertRaises(RuntimeError) as ctx:
            seed_demo_data(self.db)
        self.assertIn("Safety Collision Guard", str(ctx.exception))

    def test_invalid_timezone_aborts(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            seed_demo_data(self.db, timezone_name="Invalid/Timezone_Name")
        self.assertIn("Invalid timezone specification", str(ctx.exception))


class TestSeederCliOptions(BaseSeedDemoDataTestCase):
    """Tests H: Seeder CLI flags (--reset-passwords, --reset-task-status, --reseed-demo-data)."""

    def test_reset_passwords_rotates_hash(self) -> None:
        seed_demo_data(self.db)
        self.db.commit()

        alex_id = get_demo_user_id("demo_eng")
        creds_1 = self.db.query(UserCredentials).filter(UserCredentials.user_id == alex_id).first()
        hash_1 = creds_1.password_hash

        # Update password env var and run with reset_passwords=True
        with patch.dict(os.environ, {"DEMO_PASSWORD_ALEX_CHEN": "NewAlex#2026"}):
            report = seed_demo_data(self.db, reset_passwords=True)
            self.db.commit()
            self.assertEqual(report.passwords_reset, 4)

            creds_2 = self.db.query(UserCredentials).filter(UserCredentials.user_id == alex_id).first()
            self.assertNotEqual(creds_2.password_hash, hash_1)
            self.assertTrue(verify_password("NewAlex#2026", creds_2.password_hash))

    def test_reset_task_status_restores_baseline(self) -> None:
        seed_demo_data(self.db)
        self.db.commit()

        # Manually complete Task 1 (was pending)
        t1_id = get_demo_task_id("demo_eng", 1)
        task_1 = self.db.query(Task).filter(Task.id == t1_id).first()
        task_1.status = TaskStatus.complete
        self.db.commit()

        # Regular seed preserves status
        seed_demo_data(self.db, reset_task_status=False)
        self.db.commit()
        self.assertEqual(self.db.query(Task).filter(Task.id == t1_id).first().status, TaskStatus.complete)

        # Reset task status restores pending
        seed_demo_data(self.db, reset_task_status=True)
        self.db.commit()
        self.assertEqual(self.db.query(Task).filter(Task.id == t1_id).first().status, TaskStatus.pending)


if __name__ == "__main__":
    unittest.main()
