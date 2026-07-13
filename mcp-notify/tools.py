"""
VeriTrace Notifications – raw tool functions.

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

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

_DISCORD_WEBHOOK_URL: str | None = os.getenv("DISCORD_WEBHOOK_URL")
_SLACK_WEBHOOK_URL: str | None = os.getenv("SLACK_WEBHOOK_URL")

_TIMEOUT: int = 10  # seconds


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------

def notify_discord(message: str) -> dict:
    """Send *message* to the configured Discord webhook.

    Returns ``{"success": true}`` on a 2xx response, or
    ``{"success": false, "error": "<details>"}`` on failure.
    """
    if not _DISCORD_WEBHOOK_URL:
        return {"success": False, "error": "DISCORD_WEBHOOK_URL is not configured"}

    try:
        resp = requests.post(
            _DISCORD_WEBHOOK_URL,
            json={"content": message},
            headers={"Content-Type": "application/json"},
            timeout=_TIMEOUT,
        )
        if resp.ok:
            return {"success": True}
        return {
            "success": False,
            "error": f"Discord returned HTTP {resp.status_code}: {resp.text}",
        }
    except requests.exceptions.ConnectionError as exc:
        return {"success": False, "error": f"Connection error: {exc}"}
    except requests.exceptions.Timeout as exc:
        return {"success": False, "error": f"Request timed out: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


def notify_slack(message: str) -> dict:
    """Send *message* to the configured Slack webhook.

    Returns ``{"success": true}`` on a 2xx response, or
    ``{"success": false, "error": "<details>"}`` on failure.
    """
    if not _SLACK_WEBHOOK_URL:
        return {"success": False, "error": "SLACK_WEBHOOK_URL is not configured"}

    try:
        resp = requests.post(
            _SLACK_WEBHOOK_URL,
            json={"text": message},
            headers={"Content-Type": "application/json"},
            timeout=_TIMEOUT,
        )
        if resp.ok:
            return {"success": True}
        return {
            "success": False,
            "error": f"Slack returned HTTP {resp.status_code}: {resp.text}",
        }
    except requests.exceptions.ConnectionError as exc:
        return {"success": False, "error": f"Connection error: {exc}"}
    except requests.exceptions.Timeout as exc:
        return {"success": False, "error": f"Request timed out: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}
