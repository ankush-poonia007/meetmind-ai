"""
Unit and integration tests for Gate 4 Batch 4.5: Backend Authentication APIs.
Updated for Consent Policy System Removal:
1. Registration (POST /api/v1/auth/register): credentials, atomicity, validation, no consent required.
2. Login (POST /api/v1/auth/login): Argon2id verification, account enumeration prevention, uncredentialed handling.
3. JWT Access Tokens: issuance, signature validation, expiration, claims.
4. Current User (GET /api/v1/auth/me): identity resolution, zero credential leakage.
5. Logout (POST /api/v1/auth/logout): stateless acknowledgment.
6. Legacy API compatibility: POST /api/v1/users/register and user CRUD remain intact.
"""

from __future__ import annotations

import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import Base
from app.db.models.user import User
from app.db.models.user_credentials import UserCredentials
from app.db.session import get_db
from app.main import app


class BaseAuthAPITestCase(unittest.TestCase):
    """Base test case managing in-memory SQLite and FastAPI TestClient."""

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

    def tearDown(self) -> None:
        self.db.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def create_legacy_user(
        self, name: str = "Legacy User", email: str = "legacy@example.com"
    ) -> User:
        """Helper to create a user account without password credentials."""
        user = User(id=uuid.uuid4(), name=name, email=email)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user


# ═══════════════════════════════════════════════════════════════════════════════
# 1. USER REGISTRATION TESTS (POST /api/v1/auth/register)
# ═══════════════════════════════════════════════════════════════════════════════

class UserRegistrationAPITests(BaseAuthAPITestCase):
    """Tests registration with credentials, validation, atomicity, without consent machinery."""

    def test_registration_success(self) -> None:
        """Valid registration creates user and credentials, and returns 201 + JWT."""
        payload = {
            "first_name": "Jane",
            "last_name": "Doe",
            "mobile_number": "+1-555-019-2834",
            "email": "jane.doe@example.com",
            "password": "SecurePass123!",
        }
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertGreater(data["expires_in"], 0)

        user_info = data["user"]
        self.assertEqual(user_info["email"], "jane.doe@example.com")
        self.assertEqual(user_info["first_name"], "Jane")
        self.assertEqual(user_info["last_name"], "Doe")
        self.assertEqual(user_info["name"], "Jane Doe")
        self.assertEqual(user_info["mobile_number"], "+1-555-019-2834")
        self.assertNotIn("password", user_info)
        self.assertNotIn("password_hash", user_info)

        # Verify database records
        user = self.db.execute(
            select(User).where(User.email == "jane.doe@example.com")
        ).scalar_one()
        self.assertIsNotNone(user.credentials)
        self.assertTrue(verify_password("SecurePass123!", user.credentials.password_hash))

    def test_registration_without_optional_fields(self) -> None:
        """Registration succeeds with only mandatory fields; defaults synthesized properly."""
        payload = {
            "first_name": "John",
            "last_name": "Smith",
            "email": "john.smith@example.com",
            "password": "ValidPass123!",
        }
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data["user"]["name"], "John Smith")
        self.assertIsNone(data["user"]["mobile_number"])

    def test_registration_confirm_password_match(self) -> None:
        """Registration succeeds when confirm_password matches password."""
        payload = {
            "first_name": "Match",
            "last_name": "Pass",
            "email": "match@example.com",
            "password": "ValidPass123!",
            "confirm_password": "ValidPass123!",
        }
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_registration_confirm_password_mismatch_rejected(self) -> None:
        """Registration fails with 422 when confirm_password does not match password."""
        payload = {
            "first_name": "Mismatch",
            "last_name": "Pass",
            "email": "mismatch@example.com",
            "password": "ValidPass123!",
            "confirm_password": "DifferentPass123!",
        }
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("passwords do not match", response.text.lower())

    def test_registration_duplicate_email(self) -> None:
        """Registering with an existing email returns 409 Conflict."""
        self.create_legacy_user(email="duplicate@example.com")

        payload = {
            "first_name": "Duplicate",
            "last_name": "User",
            "email": "duplicate@example.com",
            "password": "ValidPass123!",
        }
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("already exists", response.json()["message"])

    def test_registration_weak_password_rejected(self) -> None:
        """Passwords failing complexity rules are rejected with 422 Unprocessable Entity."""
        weak_passwords = [
            "short1!",        # < 8 chars
            "TooLongPassword123!",  # > 14 chars
            "lowercase123!",  # No uppercase
            "UPPERCASE123!",  # No lowercase
            "NoNumberHere!",  # No digit
            "NoSpecialChar1", # No special
        ]
        for pwd in weak_passwords:
            payload = {
                "first_name": "Test",
                "last_name": "User",
                "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
                "password": pwd,
            }
            response = self.client.post("/api/v1/auth/register", json=payload)
            self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_registration_atomicity_on_failure(self) -> None:
        """Failed registration rolls back transaction and leaves no partial account records."""
        payload = {
            "first_name": "Fail",
            "last_name": "User",
            "email": "fail@example.com",
            "password": "ValidPass123!",
        }
        with patch.object(Session, "commit", side_effect=RuntimeError("Database commit failed")):
            with self.assertRaises(RuntimeError):
                self.client.post("/api/v1/auth/register", json=payload)

        # Confirm rollback left no records
        user = self.db.execute(select(User).where(User.email == "fail@example.com")).scalar_one_or_none()
        self.assertIsNone(user)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. USER LOGIN TESTS (POST /api/v1/auth/login)
# ═══════════════════════════════════════════════════════════════════════════════

class UserLoginAPITests(BaseAuthAPITestCase):
    """Tests user login, password verification, and generic error secrecy."""

    def setUp(self) -> None:
        super().setUp()
        reg_payload = {
            "first_name": "Alice",
            "last_name": "Tester",
            "email": "alice@example.com",
            "password": "AlicePass123!",
        }
        self.client.post("/api/v1/auth/register", json=reg_payload)

    def test_login_success(self) -> None:
        """Correct email and password returns 200, JWT token, and sanitized profile."""
        payload = {
            "email": "alice@example.com",
            "password": "AlicePass123!",
        }
        response = self.client.post("/api/v1/auth/login", json=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["email"], "alice@example.com")
        self.assertNotIn("password_hash", data["user"])

    def test_login_incorrect_password(self) -> None:
        """Incorrect password returns 401 with generic error message."""
        payload = {
            "email": "alice@example.com",
            "password": "WrongPassword1!",
        }
        response = self.client.post("/api/v1/auth/login", json=payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()["message"], "Invalid email or password.")

    def test_login_nonexistent_email(self) -> None:
        """Nonexistent email returns 401 with identical generic error (no enumeration)."""
        payload = {
            "email": "nonexistent@example.com",
            "password": "SomePassword1!",
        }
        response = self.client.post("/api/v1/auth/login", json=payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()["message"], "Invalid email or password.")

    def test_login_legacy_account_without_credentials_fails_safely(self) -> None:
        """Legacy account without a credentials record returns 401 without unhandled crash."""
        self.create_legacy_user(email="legacy_nocreds@example.com")

        payload = {
            "email": "legacy_nocreds@example.com",
            "password": "AnyPassword123!",
        }
        response = self.client.post("/api/v1/auth/login", json=payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()["message"], "Invalid email or password.")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. JWT TOKEN & IDENTITY RESOLUTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class JWTIdentityTests(BaseAuthAPITestCase):
    """Tests JWT creation, signature validation, expiration, and get_current_user."""

    def setUp(self) -> None:
        super().setUp()
        reg_payload = {
            "first_name": "Bob",
            "last_name": "Builder",
            "email": "bob@example.com",
            "password": "BobPass123!",
        }
        res = self.client.post("/api/v1/auth/register", json=reg_payload)
        self.token = res.json()["access_token"]
        self.user_id = res.json()["user"]["id"]

    def test_get_me_success(self) -> None:
        """GET /api/v1/auth/me with valid Bearer token returns authenticated profile."""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["id"], self.user_id)
        self.assertEqual(data["email"], "bob@example.com")
        self.assertNotIn("password_hash", data)

    def test_get_me_missing_token(self) -> None:
        """GET /api/v1/auth/me without Authorization header returns 401."""
        response = self.client.get("/api/v1/auth/me")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("WWW-Authenticate", response.headers)

    def test_get_me_expired_token(self) -> None:
        """Expired JWT returns 401 with WWW-Authenticate error description."""
        expired_token = create_access_token(
            subject=self.user_id,
            email="bob@example.com",
            expires_delta=timedelta(seconds=-10),  # expired 10s ago
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("expired", response.json()["message"].lower())
        self.assertIn("invalid_token", response.headers.get("WWW-Authenticate", ""))

    def test_get_me_tampered_token(self) -> None:
        """Tampered JWT signature returns 401 Unauthorized."""
        tampered_token = self.token[:-5] + "XXXXX"
        headers = {"Authorization": f"Bearer {tampered_token}"}
        response = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_me_deleted_or_missing_user(self) -> None:
        """Valid token for a user that was deleted returns 401."""
        ghost_token = create_access_token(
            subject=uuid.uuid4(),
            email="ghost@example.com",
        )
        headers = {"Authorization": f"Bearer {ghost_token}"}
        response = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("not found", response.json()["message"].lower())


# ═══════════════════════════════════════════════════════════════════════════════
# 4. STATELESS LOGOUT TESTS (POST /api/v1/auth/logout)
# ═══════════════════════════════════════════════════════════════════════════════

class StatelessLogoutAPITests(BaseAuthAPITestCase):
    """Tests stateless logout behavior."""

    def test_logout_success(self) -> None:
        """POST /api/v1/auth/logout returns 200 with clear discard instructions."""
        response = self.client.post("/api/v1/auth/logout")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("discard your access token", data["message"].lower())


# ═══════════════════════════════════════════════════════════════════════════════
# 5. LEGACY ROUTE COMPATIBILITY & REGRESSION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class LegacyRouteCompatibilityTests(BaseAuthAPITestCase):
    """Verifies that legacy /users endpoints remain 100% compatible."""

    def test_legacy_user_registration_preserved(self) -> None:
        """Legacy POST /api/v1/users/register functions without password/consent."""
        legacy_payload = {
            "name": "Legacy Engineer",
            "email": "legacy.eng@example.com",
        }
        response = self.client.post("/api/v1/users/register", json=legacy_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["name"], "Legacy Engineer")
        self.assertEqual(data["email"], "legacy.eng@example.com")

        # Verify legacy account has no credentials
        user = self.db.execute(
            select(User).where(User.email == "legacy.eng@example.com")
        ).scalar_one()
        self.assertIsNone(user.credentials)

    def test_legacy_user_get_and_update_preserved(self) -> None:
        """Legacy GET /api/v1/users/{id} and PUT /api/v1/users/{id} continue to work."""
        user = self.create_legacy_user(name="Old Name", email="old.user@example.com")

        # GET
        get_res = self.client.get(f"/api/v1/users/{user.id}")
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(get_res.json()["name"], "Old Name")

        # PUT
        put_res = self.client.put(
            f"/api/v1/users/{user.id}",
            json={"name": "New Name"},
        )
        self.assertEqual(put_res.status_code, status.HTTP_200_OK)
        self.assertEqual(put_res.json()["name"], "New Name")


if __name__ == "__main__":
    unittest.main()
