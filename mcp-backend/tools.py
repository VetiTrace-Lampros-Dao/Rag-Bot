"""
VeriTrace Backend – raw tool functions.

These functions are MCP-free so the orchestrator can call them directly.
Each function returns a plain ``dict`` matching the MCP tool contract.
Includes a debug mock for test hash 'abc123flagged' to verify tool chaining.
"""

from __future__ import annotations

import os
import pathlib

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

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
    # Debug mock for testing multi-step tool chaining
    if file_hash in ("abc123flagged", "test_hash"):
        return {
            "duplicate": True,
            "exact_match": {
                "content_id": "content_999",
                "owner": "VeriTrace Test Registry",
                "timestamp": 1721111111
            }
        }
        
    url = f"{_BASE_URL}/api/v1/verify/exact?hash={file_hash}"
    return _get(url)


def get_verification_status(content_id: str) -> dict:
    """Return the current verification status for *content_id*.

    Makes a GET request to the ``/api/v1/verify/exact`` endpoint.
    """
    if content_id == "content_999":
        return {
            "exact_match": {
                "content_id": "content_999",
                "owner": "VeriTrace Test Registry",
                "timestamp": 1721111111
            },
            "similar_matches": [
                {"content_id": "content_100", "similarity": 95.5, "hamming_distance": 2},
                {"content_id": "content_101", "similarity": 85.0, "hamming_distance": 6}
            ]
        }
        
    url = f"{_BASE_URL}/api/v1/verify/exact?hash={content_id}"
    return _get(url)


def get_similar_matches(content_id: str) -> dict:
    """Find fuzzy / perceptual-hash matches for *content_id*.

    Makes a GET request to the ``/api/v1/verify/fuzzy`` endpoint.
    """
    if content_id == "content_999":
        return {
            "similar_matches": [
                {"content_id": "content_100", "similarity": 95.5, "hamming_distance": 2},
                {"content_id": "content_101", "similarity": 85.0, "hamming_distance": 6}
            ]
        }
        
    url = f"{_BASE_URL}/api/v1/verify/fuzzy?phash={content_id}"
    return _get(url)
