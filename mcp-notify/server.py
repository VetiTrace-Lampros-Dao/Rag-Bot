"""
VeriTrace Notifications – MCP Tool Server.

Exposes two notification tools over the MCP stdio transport using FastMCP:
* ``notify_discord`` – send a message to a Discord channel via webhook
* ``notify_slack``   – send a message to a Slack channel via webhook
"""

import os
import sys
import json
from mcp.server.fastmcp import FastMCP

# Ensure the directory of this script is in sys.path to import tools.py
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import the raw helpers so all HTTP logic lives in one place.
from tools import (
    notify_discord as _notify_discord,
    notify_slack as _notify_slack,
)

mcp_server = FastMCP("veritrace-notify")

@mcp_server.tool()
def notify_discord(message: str) -> str:
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

@mcp_server.tool()
def notify_slack(message: str) -> str:
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

if __name__ == "__main__":
    mcp_server.run()
