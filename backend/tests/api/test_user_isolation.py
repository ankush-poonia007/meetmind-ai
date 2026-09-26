"""
Unit and integration tests for Gate 4 Batch 4.8: User-Specific Dashboard Data Isolation.

Validates server-side ownership authorization and complete data isolation:
1. Requests without valid JWT are rejected with 401 Unauthorized.
2. Requests with expired or malformed JWT are rejected with 401 Unauthorized.
3. User A lists only their own meetings (GET /meetings/ and GET /meetings/{user_a.id}).
4. User A lists only their own tasks (GET /tasks/ and GET /tasks/{user_a.id}).
5. User A lists only their own highlights (GET /highlights/ and GET /highlights/{user_a.id}).
6. User A attempting to access User B's data via forged user_id path parameter is rejected (404 Not Found).
7. User A retrieving User B's meeting detail is rejected (404 Not Found).
8. User A attempting to delete User B's meeting is rejected (404 Not Found), preserving DB state.
9. User A attempting to toggle User B's task status is rejected (404 Not Found), preserving DB state.
10. User A attempting to create a meeting assigned to User B is rejected (404 Not Found).
11. User A attempting to query tasks from User B's meeting is rejected (404 Not Found).
12. User A attempting to query highlights from User B's meeting is rejected (404 Not Found).
13. User A and User B can access, modify, and delete their own resources without mutual interference.
"""

from __future__ import annotations

import sys
import unittest
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.constants import InputFormat, TaskPriority, TaskStatus
from app.core.security import create_access_token
from app.db.base import Base
from app.db.models.highlight import Highlight
from app.db.models.meeting import Meeting
from app.db.models.task import Task, TaskPriority as DBTaskPriority, TaskStatus as DBTaskStatus
from app.db.models.user import User
from app.db.session import get_db
from app.main import app


class BaseUserIsolationTestCase(unittest.TestCase):
    """Sets up an isolated database session and test fixtures for User A and User B."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

        def _override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = _override_get_db
        self.client = TestClient(app)
        self.db: Session = self.SessionLocal()

        # Create User A & User B
        self.user_a = User(
            id=uuid.uuid4(),
            name="Alice Walker",
            first_name="Alice",
            last_name="Walker",
            email="alice@example.com",
        )
        self.user_b = User(
            id=uuid.uuid4(),
            name="Bob Martin",
            first_name="Bob",
            last_name="Martin",
            email="bob@example.com",
        )
        self.db.add_all([self.user_a, self.user_b])
        self.db.commit()
        self.db.refresh(self.user_a)
        self.db.refresh(self.user_b)

        # Tokens & Auth headers
        self.token_a = create_access_token(subject=self.user_a.id, email=self.user_a.email)
        self.headers_a = {"Authorization": f"Bearer {self.token_a}"}

        self.token_b = create_access_token(subject=self.user_b.id, email=self.user_b.email)
        self.headers_b = {"Authorization": f"Bearer {self.token_b}"}

        # Create Meeting A for User A
        self.meeting_a = Meeting(
            id=uuid.uuid4(),
            user_id=self.user_a.id,
            title="Alice Planning Session",
            organization="Alice Team",
            meeting_date=date(2026, 9, 25),
            meeting_time="10:00",
            raw_transcript="Alice: We need to finalize user data isolation.",
            input_format="text",
        )
        # Create Meeting B for User B
        self.meeting_b = Meeting(
            id=uuid.uuid4(),
            user_id=self.user_b.id,
            title="Bob Operations Review",
            organization="Bob Team",
            meeting_date=date(2026, 9, 26),
            meeting_time="14:00",
            raw_transcript="Bob: Reviewing cloud infrastructure and security boundaries.",
            input_format="text",
        )
        self.db.add_all([self.meeting_a, self.meeting_b])
        self.db.commit()
        self.db.refresh(self.meeting_a)
        self.db.refresh(self.meeting_b)

        # Create Tasks
        self.task_a = Task(
            id=uuid.uuid4(),
            meeting_id=self.meeting_a.id,
            user_id=self.user_a.id,
            title="Alice Isolation Task",
            description="Enforce server-side ownership",
            priority=DBTaskPriority.high,
            status=DBTaskStatus.pending,
            deadline=datetime.now(timezone.utc) + timedelta(days=1),
        )
        self.task_b = Task(
            id=uuid.uuid4(),
            meeting_id=self.meeting_b.id,
            user_id=self.user_b.id,
            title="Bob Ops Task",
            description="Verify network partitions",
            priority=DBTaskPriority.medium,
            status=DBTaskStatus.pending,
            deadline=datetime.now(timezone.utc) + timedelta(days=2),
        )
        self.db.add_all([self.task_a, self.task_b])

        # Create Highlights
        self.highlight_a = Highlight(
            id=uuid.uuid4(),
            meeting_id=self.meeting_a.id,
            user_id=self.user_a.id,
            content="Alice Decision: Lock down all dashboard endpoints.",
        )
        self.highlight_b = Highlight(
            id=uuid.uuid4(),
            meeting_id=self.meeting_b.id,
            user_id=self.user_b.id,
            content="Bob Decision: Isolate tenant resources securely.",
        )
        self.db.add_all([self.highlight_a, self.highlight_b])
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()


class TestUserSpecificDataIsolation(BaseUserIsolationTestCase):
    """Comprehensive test suite for Batch 4.8 user data isolation."""

    def test_01_requests_without_jwt_rejected(self) -> None:
        """Unauthenticated requests to meetings, tasks, and highlights return 401 Unauthorized."""
        endpoints = [
            ("GET", "/api/v1/meetings/"),
            ("GET", f"/api/v1/meetings/{self.user_a.id}"),
            ("GET", f"/api/v1/meetings/{self.meeting_a.id}/detail"),
            ("DELETE", f"/api/v1/meetings/{self.meeting_a.id}"),
            ("GET", "/api/v1/tasks/"),
            ("GET", f"/api/v1/tasks/{self.user_a.id}"),
            ("GET", f"/api/v1/tasks/{self.user_a.id}/filter"),
            ("GET", f"/api/v1/tasks/{self.user_a.id}/meeting/{self.meeting_a.id}"),
            ("PUT", f"/api/v1/tasks/{self.task_a.id}/status"),
            ("GET", "/api/v1/highlights/"),
            ("GET", f"/api/v1/highlights/{self.user_a.id}"),
            ("GET", f"/api/v1/highlights/{self.user_a.id}/meeting/{self.meeting_a.id}"),
        ]
        for method, url in endpoints:
            if method == "GET":
                res = self.client.get(url)
            elif method == "DELETE":
                res = self.client.delete(url)
            elif method == "PUT":
                res = self.client.put(url, json={"status": "complete"})
            self.assertEqual(
                res.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Expected 401 for unauthenticated {method} {url}, got {res.status_code}",
            )

    def test_02_requests_with_invalid_and_expired_jwt_rejected(self) -> None:
        """Malformed or expired tokens return 401 Unauthorized."""
        # 1. Malformed token
        res_malformed = self.client.get(
            "/api/v1/meetings/",
            headers={"Authorization": "Bearer not.a.valid.jwt.signature"},
        )
        self.assertEqual(res_malformed.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Expired token
        expired_token = create_access_token(
            subject=self.user_a.id,
            email=self.user_a.email,
            expires_delta=timedelta(seconds=-60),
        )
        res_expired = self.client.get(
            "/api/v1/meetings/",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        self.assertEqual(res_expired.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_03_user_a_lists_only_own_meetings(self) -> None:
        """User A can list only their own meetings, never User B's meetings."""
        # Canonical route
        res_canon = self.client.get("/api/v1/meetings/", headers=self.headers_a)
        self.assertEqual(res_canon.status_code, status.HTTP_200_OK)
        items_canon = res_canon.json()
        self.assertEqual(len(items_canon), 1)
        self.assertEqual(items_canon[0]["id"], str(self.meeting_a.id))
        self.assertEqual(items_canon[0]["title"], "Alice Planning Session")

        # Parameterized route
        res_param = self.client.get(f"/api/v1/meetings/{self.user_a.id}", headers=self.headers_a)
        self.assertEqual(res_param.status_code, status.HTTP_200_OK)
        items_param = res_param.json()
        self.assertEqual(len(items_param), 1)
        self.assertEqual(items_param[0]["id"], str(self.meeting_a.id))

    def test_04_user_a_lists_only_own_tasks(self) -> None:
        """User A can list only their own tasks, never User B's tasks."""
        # Canonical route
        res = self.client.get("/api/v1/tasks/", headers=self.headers_a)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tasks = res.json()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["id"], str(self.task_a.id))
        self.assertEqual(tasks[0]["title"], "Alice Isolation Task")

        # Filter route
        res_filter = self.client.get(
            f"/api/v1/tasks/{self.user_a.id}/filter?status=pending",
            headers=self.headers_a,
        )
        self.assertEqual(res_filter.status_code, status.HTTP_200_OK)
        filtered_tasks = res_filter.json()
        self.assertEqual(len(filtered_tasks), 1)
        self.assertEqual(filtered_tasks[0]["id"], str(self.task_a.id))

    def test_05_user_a_lists_only_own_highlights(self) -> None:
        """User A can list only their own highlights, never User B's highlights."""
        res = self.client.get("/api/v1/highlights/", headers=self.headers_a)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        highlights = data.get("highlights", [])
        self.assertEqual(len(highlights), 1)
        self.assertEqual(highlights[0]["id"], str(self.highlight_a.id))
        self.assertEqual(highlights[0]["content"], "Alice Decision: Lock down all dashboard endpoints.")

    def test_06_user_a_requests_user_b_data_using_forged_user_id(self) -> None:
        """User A providing User B's user_id in path parameters is rejected with 404 (InvalidOwnershipError)."""
        # 1. Meetings for User B
        res_m = self.client.get(f"/api/v1/meetings/{self.user_b.id}", headers=self.headers_a)
        self.assertEqual(res_m.status_code, status.HTTP_404_NOT_FOUND)

        # 2. Tasks for User B
        res_t = self.client.get(f"/api/v1/tasks/{self.user_b.id}", headers=self.headers_a)
        self.assertEqual(res_t.status_code, status.HTTP_404_NOT_FOUND)

        # 3. Tasks filter for User B
        res_tf = self.client.get(f"/api/v1/tasks/{self.user_b.id}/filter", headers=self.headers_a)
        self.assertEqual(res_tf.status_code, status.HTTP_404_NOT_FOUND)

        # 4. Highlights for User B
        res_h = self.client.get(f"/api/v1/highlights/{self.user_b.id}", headers=self.headers_a)
        self.assertEqual(res_h.status_code, status.HTTP_404_NOT_FOUND)

    def test_07_user_a_retrieves_user_b_meeting_detail_rejected(self) -> None:
        """User A attempting to view User B's meeting detail by meeting_id is rejected with 404."""
        res = self.client.get(
            f"/api/v1/meetings/{self.meeting_b.id}/detail",
            headers=self.headers_a,
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        # Ensure transcript is not exposed
        self.assertNotIn("Bob: Reviewing cloud infrastructure", res.text)

    def test_08_user_a_deletes_user_b_meeting_rejected(self) -> None:
        """User A attempting to delete User B's meeting is rejected with 404 and record is preserved."""
        res = self.client.delete(
            f"/api/v1/meetings/{self.meeting_b.id}",
            headers=self.headers_a,
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # Verify database record still exists
        meeting_in_db = self.db.query(Meeting).filter(Meeting.id == self.meeting_b.id).first()
        self.assertIsNotNone(meeting_in_db)
        self.assertEqual(meeting_in_db.title, "Bob Operations Review")

    def test_09_user_a_changes_user_b_task_status_rejected(self) -> None:
        """User A attempting to modify User B's task status is rejected with 404 and DB state is unchanged."""
        res = self.client.put(
            f"/api/v1/tasks/{self.task_b.id}/status",
            json={"status": "complete"},
            headers=self.headers_a,
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # Verify task status remains pending in database
        self.db.expire_all()
        task_in_db = self.db.query(Task).filter(Task.id == self.task_b.id).first()
        self.assertEqual(task_in_db.status, DBTaskStatus.pending)

    def test_10_user_a_creates_meeting_with_user_b_id_rejected(self) -> None:
        """User A attempting to submit a meeting assigned to User B is rejected with 404."""
        payload = {
            "user_id": str(self.user_b.id),
            "meeting_date": "2026-09-25",
            "meeting_time": "16:00",
            "organization": "Spoofed Org",
            "input_format": "text",
            "raw_transcript": "Spoofed meeting transcript.",
        }
        res = self.client.post("/api/v1/meetings/", json=payload, headers=self.headers_a)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # Confirm no meeting was created with title "Spoofed Org"
        spoofed = self.db.query(Meeting).filter(Meeting.organization == "Spoofed Org").first()
        self.assertIsNone(spoofed)

    def test_11_user_a_associates_task_with_user_b_meeting_rejected(self) -> None:
        """User A attempting to query tasks from User B's meeting is rejected with 404."""
        res = self.client.get(
            f"/api/v1/tasks/{self.user_a.id}/meeting/{self.meeting_b.id}",
            headers=self.headers_a,
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_12_user_a_associates_highlight_with_user_b_meeting_rejected(self) -> None:
        """User A attempting to query highlights from User B's meeting is rejected with 404."""
        res = self.client.get(
            f"/api/v1/highlights/{self.user_a.id}/meeting/{self.meeting_b.id}",
            headers=self.headers_a,
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_13_user_a_and_user_b_access_own_resources_allowed(self) -> None:
        """Both users can independently read, update, and delete their own resources without collision."""
        # User A reads own detail
        res_a_detail = self.client.get(f"/api/v1/meetings/{self.meeting_a.id}/detail", headers=self.headers_a)
        self.assertEqual(res_a_detail.status_code, status.HTTP_200_OK)

        # User B reads own detail
        res_b_detail = self.client.get(f"/api/v1/meetings/{self.meeting_b.id}/detail", headers=self.headers_b)
        self.assertEqual(res_b_detail.status_code, status.HTTP_200_OK)

        # User A updates own task status
        res_a_task = self.client.put(
            f"/api/v1/tasks/{self.task_a.id}/status",
            json={"status": "complete"},
            headers=self.headers_a,
        )
        self.assertEqual(res_a_task.status_code, status.HTTP_200_OK)
        self.assertEqual(res_a_task.json()["status"], "complete")

        # User B updates own task status
        res_b_task = self.client.put(
            f"/api/v1/tasks/{self.task_b.id}/status",
            json={"status": "complete"},
            headers=self.headers_b,
        )
        self.assertEqual(res_b_task.status_code, status.HTTP_200_OK)
        self.assertEqual(res_b_task.json()["status"], "complete")

        # User A deletes own meeting
        res_del_a = self.client.delete(f"/api/v1/meetings/{self.meeting_a.id}", headers=self.headers_a)
        self.assertEqual(res_del_a.status_code, status.HTTP_204_NO_CONTENT)

        # User B's meeting still intact!
        res_b_check = self.client.get(f"/api/v1/meetings/{self.meeting_b.id}/detail", headers=self.headers_b)
        self.assertEqual(res_b_check.status_code, status.HTTP_200_OK)


if __name__ == "__main__":
    unittest.main()
