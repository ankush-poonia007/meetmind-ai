"""
Unit and integration tests for backend CORS configuration and parsing.
Verifies that:
1. Settings parses CORS_ORIGINS from environment variables (comma-separated, JSON lists, single origins).
2. Trailing slashes and path components are sanitized.
3. Strings are not split character-by-character.
4. FastAPI CORSMiddleware enforces allowed origins correctly.
"""

import sys
import unittest
from unittest.mock import patch

# Ensure backend and site-packages are on sys.path (standard library takes precedence)
import uuid  # preload standard library uuid
sys.path.append(r"D:\PROJECTS\meetmind-ai\.venv\Lib\site-packages")
sys.path.append(r"D:\PROJECTS\meetmind-ai\backend")

from app.core.settings import Settings
from fastapi.testclient import TestClient
from app.main import app


class TestCorsConfiguration(unittest.TestCase):
    """Test suite for CORS_ORIGINS parsing and CORSMiddleware behavior."""

    def test_default_cors_origins(self):
        """When CORS_ORIGINS is not set, default local dev origins should be loaded."""
        with patch.dict("os.environ", {}, clear=False):
            # Remove CORS_ORIGINS from env if present
            import os
            os.environ.pop("CORS_ORIGINS", None)
            s = Settings(_env_file=None)
            self.assertIn("http://localhost:5173", s.cors_origins)
            self.assertIn("http://127.0.0.1:5173", s.cors_origins)
            self.assertIn("http://localhost:3000", s.cors_origins)
            self.assertIn("http://localhost:8501", s.cors_origins)

    def test_comma_separated_origins(self):
        """Comma-separated origins must be parsed into distinct items, not characters."""
        with patch.dict("os.environ", {"CORS_ORIGINS": "https://meetmind-ai.vercel.app, https://meetmind.ai"}):
            s = Settings(_env_file=None)
            self.assertEqual(
                s.cors_origins,
                ["https://meetmind-ai.vercel.app", "https://meetmind.ai"],
            )

    def test_single_origin_not_split_into_chars(self):
        """A single origin must remain a 1-element list, not a list of characters."""
        with patch.dict("os.environ", {"CORS_ORIGINS": "https://meetmind-ai.vercel.app"}):
            s = Settings(_env_file=None)
            self.assertEqual(len(s.cors_origins), 1)
            self.assertEqual(s.cors_origins[0], "https://meetmind-ai.vercel.app")
            self.assertNotEqual(s.cors_origins[0], "h")

    def test_trailing_slash_sanitization(self):
        """Accidental trailing slashes in CORS_ORIGINS should be stripped."""
        with patch.dict("os.environ", {"CORS_ORIGINS": "https://meetmind-ai.vercel.app/"}):
            s = Settings(_env_file=None)
            self.assertEqual(s.cors_origins, ["https://meetmind-ai.vercel.app"])

    def test_path_component_sanitization(self):
        """Accidental URL paths in CORS_ORIGINS should be stripped down to origin (scheme://host:port)."""
        with patch.dict("os.environ", {"CORS_ORIGINS": "https://meetmind-ai.vercel.app/api/v1, http://localhost:5173/workspace"}):
            s = Settings(_env_file=None)
            self.assertEqual(
                s.cors_origins,
                ["https://meetmind-ai.vercel.app", "http://localhost:5173"],
            )

    def test_json_array_format(self):
        """JSON array format for CORS_ORIGINS must be supported."""
        with patch.dict("os.environ", {"CORS_ORIGINS": '["https://preview-1.vercel.app", "https://preview-2.vercel.app"]'}):
            s = Settings(_env_file=None)
            self.assertEqual(
                s.cors_origins,
                ["https://preview-1.vercel.app", "https://preview-2.vercel.app"],
            )

    def test_empty_string_falls_back_to_defaults(self):
        """Empty string for CORS_ORIGINS must fall back to safe default local dev origins."""
        with patch.dict("os.environ", {"CORS_ORIGINS": ""}):
            s = Settings(_env_file=None)
            self.assertIn("http://localhost:5173", s.cors_origins)

    def test_cors_middleware_preflight_allowed_origin(self):
        """FastAPI TestClient preflight request from allowed origin returns 200 and CORS headers."""
        client = TestClient(app)
        response = client.options(
            "/api/v1/meetings/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:5173",
        )

    def test_cors_middleware_preflight_disallowed_origin(self):
        """FastAPI TestClient preflight request from disallowed origin does not grant CORS origin."""
        client = TestClient(app)
        response = client.options(
            "/api/v1/meetings/",
            headers={
                "Origin": "http://unauthorized-domain.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORSMiddleware returns 400 for disallowed preflights or omits allow-origin header
        self.assertNotEqual(
            response.headers.get("access-control-allow-origin"),
            "http://unauthorized-domain.com",
        )


if __name__ == "__main__":
    unittest.main()
