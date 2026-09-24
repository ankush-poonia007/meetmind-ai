"""
MeetMind AI — API Client.

Provides a centralized, reusable HTTP client for communicating with the
FastAPI backend. Reads configuration from environment variables.
All API calls are isolated from page-rendering logic.

Usage:
    from services.api_client import api
    response = api.get("/users/{user_id}")
"""

import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

# Load frontend .env
load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
REQUEST_TIMEOUT: float = 30.0


class APIError(Exception):
    """Raised when an API request fails or returns an error response."""

    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class MeetMindAPIClient:
    """
    Reusable HTTP client wrapping httpx for FastAPI backend communication.

    - Reads API_BASE_URL from .env
    - Uses /api/v1 prefix
    - Handles connection failures and error responses gracefully
    - Never hardcodes API secrets or credentials
    """

    def __init__(self, base_url: str = API_BASE_URL, timeout: float = REQUEST_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _build_url(self, endpoint: str) -> str:
        """Constructs the full URL from the endpoint path."""
        clean_endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{clean_endpoint}"

    def _handle_response(self, response: httpx.Response) -> Any:
        """Processes the HTTP response, raising APIError on failure."""
        if response.status_code >= 400:
            try:
                error_body = response.json()
            except Exception:
                error_body = {"message": response.text}

            raise APIError(
                message=error_body.get("message", f"Request failed with status {response.status_code}"),
                status_code=response.status_code,
                details=error_body.get("details", {}),
            )

        if response.status_code == 204:
            return None

        try:
            return response.json()
        except Exception:
            return response.text

    def get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """Sends a GET request to the backend API."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self._build_url(endpoint), params=params)
                return self._handle_response(response)
        except httpx.ConnectError:
            raise APIError("Unable to connect to the backend server. Please ensure it is running.", status_code=0)
        except httpx.TimeoutException:
            raise APIError("Request timed out. The backend server may be overloaded.", status_code=0)
        except APIError:
            raise
        except Exception as exc:
            raise APIError(f"Unexpected error: {exc}", status_code=0)

    def post(self, endpoint: str, json: Optional[dict] = None, params: Optional[dict] = None) -> Any:
        """Sends a POST request to the backend API."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self._build_url(endpoint), json=json, params=params)
                return self._handle_response(response)
        except httpx.ConnectError:
            raise APIError("Unable to connect to the backend server. Please ensure it is running.", status_code=0)
        except httpx.TimeoutException:
            raise APIError("Request timed out. The backend server may be overloaded.", status_code=0)
        except APIError:
            raise
        except Exception as exc:
            raise APIError(f"Unexpected error: {exc}", status_code=0)

    def put(self, endpoint: str, json: Optional[dict] = None) -> Any:
        """Sends a PUT request to the backend API."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.put(self._build_url(endpoint), json=json)
                return self._handle_response(response)
        except httpx.ConnectError:
            raise APIError("Unable to connect to the backend server. Please ensure it is running.", status_code=0)
        except httpx.TimeoutException:
            raise APIError("Request timed out. The backend server may be overloaded.", status_code=0)
        except APIError:
            raise
        except Exception as exc:
            raise APIError(f"Unexpected error: {exc}", status_code=0)

    def delete(self, endpoint: str) -> Any:
        """Sends a DELETE request to the backend API."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.delete(self._build_url(endpoint))
                return self._handle_response(response)
        except httpx.ConnectError:
            raise APIError("Unable to connect to the backend server. Please ensure it is running.", status_code=0)
        except httpx.TimeoutException:
            raise APIError("Request timed out. The backend server may be overloaded.", status_code=0)
        except APIError:
            raise
        except Exception as exc:
            raise APIError(f"Unexpected error: {exc}", status_code=0)

    def health_check(self) -> bool:
        """
        Tests connectivity to the backend health endpoint.
        Returns True if the backend is reachable, False otherwise.
        """
        try:
            # Health endpoint is at /health (not under /api/v1)
            base = self.base_url.replace("/api/v1", "").rstrip("/")
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{base}/health")
                return response.status_code == 200
        except Exception:
            return False


# ── Singleton Instance ───────────────────────────────────────────────────────

api = MeetMindAPIClient()
