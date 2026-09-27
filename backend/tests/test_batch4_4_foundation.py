"""
Unit and integration tests for Gate 4 Batch 4.4: Authentication & Database Foundation.
1. Password security foundation (Argon2id hashing, RFC 9106 parameterization, salting, verification).
2. Password complexity validation (8-14 chars, upper, lower, number, special char).
3. JWT configuration foundation (settings loading, algorithm, expiration, safe validation).
4. User model compatibility (backward compatibility of name/email, first_name, last_name, mobile_number).
5. UserCredentials model (1:1 relationship with User, cascade deletion, separation of credentials).
6. Alembic migration chain integrity (e8c9b1d2e3f4 -> a4f8d1c2b3e5 -> b2e4f6a8c0d2).
"""

from __future__ import annotations

import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.security import (
    ARGON2_HASH_LEN,
    ARGON2_MEMORY_COST,
    ARGON2_PARALLELISM,
    ARGON2_SALT_LEN,
    ARGON2_TIME_COST,
    hash_password,
    validate_password_complexity,
    verify_password,
)
from app.core.settings import Settings, settings
from app.db.base import Base
from app.db.models.user import User
from app.db.models.user_credentials import UserCredentials


class PasswordSecurityFoundationTests(unittest.TestCase):
    """Tests password hashing, verification, complexity rules, and salting."""

    def test_argon2id_parameters_defined(self) -> None:
        """Explicit RFC 9106 parameters must be configured."""
        self.assertEqual(ARGON2_TIME_COST, 3)
        self.assertEqual(ARGON2_MEMORY_COST, 65536)  # 64 MiB
        self.assertEqual(ARGON2_PARALLELISM, 4)
        self.assertEqual(ARGON2_HASH_LEN, 32)
        self.assertEqual(ARGON2_SALT_LEN, 16)

    def test_hash_password_produces_non_plaintext_hash(self) -> None:
        """Hashing must produce a standard argon2id encoded string, not plaintext."""
        raw_pw = "ValidPass123!"
        hashed = hash_password(raw_pw)

        self.assertNotEqual(raw_pw, hashed)
        self.assertTrue(hashed.startswith("$argon2id$v=19$m=65536,t=3,p=4$"))
        self.assertGreater(len(hashed), 50)

    def test_verify_password_success(self) -> None:
        """Correct password candidate must verify successfully."""
        raw_pw = "ValidPass123!"
        hashed = hash_password(raw_pw)
        self.assertTrue(verify_password(raw_pw, hashed))

    def test_verify_password_failure_mismatch(self) -> None:
        """Incorrect password candidate must fail verification."""
        raw_pw = "ValidPass123!"
        hashed = hash_password(raw_pw)
        self.assertFalse(verify_password("WrongPass123!", hashed))
        self.assertFalse(verify_password("validpass123!", hashed))

    def test_verify_password_empty_or_malformed(self) -> None:
        """Empty candidates or malformed hashes must fail safely without raising unhandled errors."""
        self.assertFalse(verify_password("", "$argon2id$v=19$m=65536,t=3,p=4$..."))
        self.assertFalse(verify_password("ValidPass123!", ""))
        self.assertFalse(verify_password("ValidPass123!", "not_a_valid_argon2_hash"))

    def test_unique_salts_produce_distinct_hashes(self) -> None:
        """Hashing the same password twice must yield different hashes due to OS entropy salting."""
        raw_pw = "ValidPass123!"
        hash1 = hash_password(raw_pw)
        hash2 = hash_password(raw_pw)

        self.assertNotEqual(hash1, hash2)
        self.assertTrue(verify_password(raw_pw, hash1))
        self.assertTrue(verify_password(raw_pw, hash2))

    def test_password_complexity_valid_cases(self) -> None:
        """Valid passwords within 8-14 chars meeting all criteria must pass."""
        valid_passwords = [
            "Passw0rd!",
            "MeetMind#2026",
            "A1b2C3d4$",
            "Secret_99",
            "Valid123@#",
        ]
        for pw in valid_passwords:
            is_valid, msg = validate_password_complexity(pw)
            self.assertTrue(is_valid, f"Expected {pw} to be valid, got: {msg}")
            self.assertEqual(msg, "")

    def test_password_complexity_invalid_cases(self) -> None:
        """Invalid passwords must fail with descriptive error messages."""
        test_cases = [
            ("Short1!", "at least 8 characters"),
            ("VeryLongPassword123!", "at most 14 characters"),
            ("lowercase123!", "uppercase letter"),
            ("UPPERCASE123!", "lowercase letter"),
            ("NoNumberHere!", "number"),
            ("NoSpecialChar1", "special character"),
        ]
        for pw, expected_error in test_cases:
            is_valid, msg = validate_password_complexity(pw)
            self.assertFalse(is_valid, f"Expected {pw} to fail complexity rules")
            self.assertIn(expected_error, msg)

    def test_hash_password_rejects_invalid_complexity(self) -> None:
        """hash_password must raise ValueError if password fails complexity validation."""
        with self.assertRaises(ValueError) as ctx:
            hash_password("short1!")
        self.assertIn("at least 8 characters", str(ctx.exception))


class JWTConfigurationTests(unittest.TestCase):
    """Tests JWT configuration foundation and safe production validation."""

    def test_jwt_defaults(self) -> None:
        """Default development settings must provide explicit algorithm and expiration."""
        self.assertTrue(hasattr(settings, "jwt_secret_key"))
        self.assertTrue(hasattr(settings, "jwt_algorithm"))
        self.assertTrue(hasattr(settings, "jwt_access_token_expire_minutes"))

        self.assertEqual(settings.jwt_algorithm, "HS256")
        self.assertEqual(settings.jwt_access_token_expire_minutes, 1440)
        self.assertGreaterEqual(len(settings.jwt_secret_key), 32)

    def test_validate_security_configuration_production_failure(self) -> None:
        """In production, missing or default dev secrets must fail safely."""
        prod_settings_with_dev_key = Settings(
            app_env="production",
            jwt_secret_key="meetmind-dev-jwt-secret-key-at-least-32-chars-long!",
        )
        with self.assertRaises(ValueError) as ctx:
            prod_settings_with_dev_key.validate_security_configuration()
        self.assertIn("JWT_SECRET_KEY must be explicitly configured", str(ctx.exception))

        prod_settings_short_key = Settings(
            app_env="production",
            jwt_secret_key="too-short-key",
        )
        with self.assertRaises(ValueError) as ctx:
            prod_settings_short_key.validate_security_configuration()
        self.assertIn("at least 32 characters", str(ctx.exception))

    def test_validate_security_configuration_production_success(self) -> None:
        """In production, a strong non-default secret must pass validation."""
        prod_settings_valid = Settings(
            app_env="production",
            jwt_secret_key="prod-ultra-secure-random-32-byte-hex-string-for-jwt-signing!",
        )
        prod_settings_valid.validate_security_configuration()


class DatabaseFoundationModelTests(unittest.TestCase):
    """Tests database models: User, UserCredentials, and their relationships."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db: Session = self.SessionLocal()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_user_model_backward_compatibility(self) -> None:
        """Existing user record structure (name, email) must persist and remain functional without new fields."""
        user_id = uuid.uuid4()
        legacy_user = User(
            id=user_id,
            name="Legacy User",
            email="legacy@meetmind.ai",
        )
        self.db.add(legacy_user)
        self.db.commit()

        loaded = self.db.execute(select(User).where(User.id == user_id)).scalar_one()
        self.assertEqual(loaded.name, "Legacy User")
        self.assertEqual(loaded.email, "legacy@meetmind.ai")
        self.assertIsNone(loaded.first_name)
        self.assertIsNone(loaded.last_name)
        self.assertIsNone(loaded.mobile_number)
        self.assertIsNone(loaded.credentials)

    def test_user_model_with_new_profile_fields(self) -> None:
        """New profile fields (first_name, last_name, mobile_number) must persist accurately."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            name="Alice Smith",
            first_name="Alice",
            last_name="Smith",
            mobile_number="+1-555-019-2834",
            email="alice.smith@meetmind.ai",
        )
        self.db.add(user)
        self.db.commit()

        loaded = self.db.execute(select(User).where(User.id == user_id)).scalar_one()
        self.assertEqual(loaded.first_name, "Alice")
        self.assertEqual(loaded.last_name, "Smith")
        self.assertEqual(loaded.mobile_number, "+1-555-019-2834")

    def test_mobile_number_non_uniqueness(self) -> None:
        """Mobile numbers must not be unique; multiple users can share or omit mobile numbers."""
        u1 = User(
            id=uuid.uuid4(),
            name="User One",
            email="u1@example.com",
            mobile_number="+1-555-123-4567",
        )
        u2 = User(
            id=uuid.uuid4(),
            name="User Two",
            email="u2@example.com",
            mobile_number="+1-555-123-4567",
        )
        self.db.add_all([u1, u2])
        self.db.commit()

        self.assertEqual(u1.mobile_number, u2.mobile_number)

    def test_email_uniqueness_preserved(self) -> None:
        """User email uniqueness constraint must be preserved."""
        u1 = User(id=uuid.uuid4(), name="User One", email="duplicate@example.com")
        self.db.add(u1)
        self.db.commit()

        u2 = User(id=uuid.uuid4(), name="User Two", email="duplicate@example.com")
        self.db.add(u2)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_user_credentials_one_to_one_relationship(self) -> None:
        """UserCredentials must establish a bidirectional 1:1 relationship with User."""
        user = User(
            id=uuid.uuid4(),
            name="Cred User",
            email="cred@meetmind.ai",
        )
        self.db.add(user)
        self.db.commit()

        hashed = hash_password("SecurePass123!")
        creds = UserCredentials(
            user_id=user.id,
            password_hash=hashed,
        )
        self.db.add(creds)
        self.db.commit()

        self.db.refresh(user)
        self.assertIsNotNone(user.credentials)
        self.assertEqual(user.credentials.user_id, user.id)
        self.assertEqual(user.credentials.password_hash, hashed)
        self.assertEqual(user.credentials.user.email, "cred@meetmind.ai")

    def test_user_credentials_cannot_duplicate(self) -> None:
        """A user cannot have multiple credentials records (user_id PK constraint)."""
        user = User(id=uuid.uuid4(), name="Single Cred", email="single@meetmind.ai")
        self.db.add(user)
        self.db.commit()

        c1 = UserCredentials(user_id=user.id, password_hash=hash_password("PassOne123!"))
        self.db.add(c1)
        self.db.commit()

        c2 = UserCredentials(user_id=user.id, password_hash=hash_password("PassTwo123!"))
        self.db.add(c2)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_user_credentials_cascade_deletion(self) -> None:
        """Deleting a user must cascade and remove their credentials record."""
        user = User(id=uuid.uuid4(), name="Delete Me", email="delete@meetmind.ai")
        self.db.add(user)
        self.db.commit()

        creds = UserCredentials(user_id=user.id, password_hash=hash_password("DeletePass123!"))
        self.db.add(creds)
        self.db.commit()

        self.db.delete(user)
        self.db.commit()

        remaining_creds = self.db.execute(
            select(UserCredentials).where(UserCredentials.user_id == user.id)
        ).scalar_one_or_none()
        self.assertIsNone(remaining_creds)


class AlembicMigrationStructureTests(unittest.TestCase):
    """Tests Alembic migration revision scripts for syntax, hooks, and down_revision linkage."""

    def test_migration_chain_integrity(self) -> None:
        """All migration scripts must import cleanly and form a continuous chain."""
        import importlib.util

        alembic_versions_dir = Path(__file__).resolve().parent.parent / "alembic" / "versions"

        # Check e8c9b1d2e3f4
        mig1_path = alembic_versions_dir / "e8c9b1d2e3f4_user_auth_and_consent_foundation.py"
        self.assertTrue(mig1_path.exists(), f"Migration file not found at {mig1_path}")
        spec1 = importlib.util.spec_from_file_location("mig1", str(mig1_path))
        mig1 = importlib.util.module_from_spec(spec1)
        spec1.loader.exec_module(mig1)

        self.assertEqual(mig1.revision, "e8c9b1d2e3f4")
        self.assertEqual(mig1.down_revision, "7a82b9c01d2e")
        self.assertTrue(callable(mig1.upgrade))
        self.assertTrue(callable(mig1.downgrade))

        # Check a4f8d1c2b3e5 (Batch 4.4 Consent Corrections)
        mig2_path = alembic_versions_dir / "a4f8d1c2b3e5_remove_implicit_consent_defaults.py"
        self.assertTrue(mig2_path.exists(), f"Migration file not found at {mig2_path}")
        spec2 = importlib.util.spec_from_file_location("mig2", str(mig2_path))
        mig2 = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(mig2)

        self.assertEqual(mig2.revision, "a4f8d1c2b3e5")
        self.assertEqual(mig2.down_revision, "e8c9b1d2e3f4")
        self.assertTrue(callable(mig2.upgrade))
        self.assertTrue(callable(mig2.downgrade))

        # Check b2e4f6a8c0d2 (Removal of user_consents table)
        mig3_path = alembic_versions_dir / "b2e4f6a8c0d2_drop_user_consents_table.py"
        self.assertTrue(mig3_path.exists(), f"Migration file not found at {mig3_path}")
        spec3 = importlib.util.spec_from_file_location("mig3", str(mig3_path))
        mig3 = importlib.util.module_from_spec(spec3)
        spec3.loader.exec_module(mig3)

        self.assertEqual(mig3.revision, "b2e4f6a8c0d2")
        self.assertEqual(mig3.down_revision, "a4f8d1c2b3e5")
        self.assertTrue(callable(mig3.upgrade))
        self.assertTrue(callable(mig3.downgrade))


if __name__ == "__main__":
    unittest.main()
