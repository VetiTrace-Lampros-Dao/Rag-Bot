"""
VeriTrace Backend – raw tool functions.

These functions are MCP-free so the orchestrator can call them directly.
Each function returns a plain ``dict`` matching the MCP tool contract.
"""

from __future__ import annotations

import os
import pathlib

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Walk up from this file to the project root to locate .env
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

_BASE_URL: str = os.getenv(
    "VERITRACE_API_BASE_URL", "http://localhost:8080"
).rstrip("/")

_TIMEOUT: int = 10  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(url: str) -> dict:
    """Issue a GET request and return the parsed JSON response.

    On connection / timeout errors return a structured error dict instead
    of raising so that callers always receive a serialisable result.
    """
    try:
        resp = requests.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError as exc:
        return {
            "error": "backend_unreachable",
            "message": f"Connection error: {exc}",
        }
    except requests.exceptions.Timeout as exc:
        return {
            "error": "backend_unreachable",
            "message": f"Request timed out after {_TIMEOUT}s: {exc}",
        }
    except requests.exceptions.HTTPError as exc:
        return {
            "error": "http_error",
            "message": f"HTTP {exc.response.status_code}: {exc}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "error": "unexpected_error",
            "message": str(exc),
        }


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------

def check_duplicate(file_hash: str) -> dict:
    """Check whether an exact duplicate of *file_hash* exists on-chain.

    Makes a GET request to the ``/api/v1/verify/exact`` endpoint.
    """
    url = f"{_BASE_URL}/api/v1/verify/exact?hash={file_hash}"
    return _get(url)


def get_verification_status(content_id: str) -> dict:
    """Return the current verification status for *content_id*.

    Makes a GET request to the ``/api/v1/verify/exact`` endpoint.
    """
    url = f"{_BASE_URL}/api/v1/verify/exact?hash={content_id}"
    return _get(url)


def get_similar_matches(content_id: str) -> dict:
    """Find fuzzy / perceptual-hash matches for *content_id*.

    Makes a GET request to the ``/api/v1/verify/fuzzy`` endpoint.
    """
    url = f"{_BASE_URL}/api/v1/verify/fuzzy?phash={content_id}"
    return _get(url)
