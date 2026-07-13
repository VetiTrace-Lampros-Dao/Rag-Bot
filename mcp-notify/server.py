"""
VeriTrace Notifications – MCP Tool Server.

Exposes two notification tools over the MCP stdio transport:

* ``notify_discord`` – send a message to a Discord channel via webhook
* ``notify_slack``   – send a message to a Slack channel via webhook

Run directly:
    python mcp-notify/server.py
"""

from __future__ import annotations

import asyncio
import json
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server

# Import the raw helpers so all HTTP logic lives in one place.
from tools import (  # type: ignore[import-untyped]
    notify_discord as _notify_discord,
    notify_slack as _notify_slack,
)

# ---------------------------------------------------------------------------
# MCP Server setup
# ---------------------------------------------------------------------------

server = Server("veritrace-notify")


@server.tool()
async def notify_discord(message: str) -> str:
    """Send a notification to the configured Discord channel.

    Parameters
    ----------
    message : str
        The message text to post.

    Returns
    -------
    str
        JSON-encoded result indicating success or failure.
    """
    result = _notify_discord(message)
    return json.dumps(result)


@server.tool()
async def notify_slack(message: str) -> str:
    """Send a notification to the configured Slack channel.

    Parameters
    ----------
    message : str
        The message text to post.

    Returns
    -------
    str
        JSON-encoded result indicating success or failure.
    """
    result = _notify_slack(message)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

async def main() -> None:
    """Run the MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
