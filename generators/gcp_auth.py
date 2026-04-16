"""Google Cloud service account auth helper for Vertex AI.

Loads credentials from a JSON key file, caches them, and refreshes access tokens
automatically. All Vertex endpoints (text, image, vision) go through here.
"""
from __future__ import annotations

import threading
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2 import service_account

from cli import config as cfg

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
_lock = threading.Lock()
_credentials: service_account.Credentials | None = None
_project_id: str | None = None


def _load_credentials() -> tuple[service_account.Credentials, str]:
    """Load service account credentials from the configured JSON path."""
    global _credentials, _project_id

    with _lock:
        if _credentials is not None and _project_id is not None:
            return _credentials, _project_id

        key_path = cfg.get("vertex.credentials_path", "vertex-key.json")
        path = Path(key_path)
        if not path.is_absolute():
            # Resolve relative to repo root
            repo_root = Path(__file__).resolve().parent.parent
            path = repo_root / key_path

        if not path.exists():
            raise RuntimeError(
                f"Vertex service account JSON not found at {path}. "
                f"Set vertex.credentials_path in config.yml."
            )

        creds = service_account.Credentials.from_service_account_file(
            str(path), scopes=_SCOPES
        )
        _credentials = creds
        _project_id = creds.project_id
        return _credentials, _project_id


def get_access_token() -> str:
    """Return a fresh OAuth2 access token (refreshes automatically)."""
    creds, _ = _load_credentials()
    if not creds.valid:
        creds.refresh(Request())
    return creds.token


def get_project_id() -> str:
    """Return the GCP project ID from the service account JSON."""
    _, project_id = _load_credentials()
    return project_id


def get_location() -> str:
    """Return the Vertex AI region (default us-central1)."""
    return cfg.get("vertex.location", "us-central1")


def auth_headers() -> dict:
    """Return standard auth headers for Vertex REST calls."""
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }


def vertex_url(model: str, method: str = "generateContent") -> str:
    """Build a Vertex AI URL for a given model (regional or global)."""
    project = get_project_id()
    location = get_location()
    host = "aiplatform.googleapis.com" if location == "global" else f"{location}-aiplatform.googleapis.com"
    return (
        f"https://{host}/v1/projects/{project}"
        f"/locations/{location}/publishers/google/models/{model}:{method}"
    )
