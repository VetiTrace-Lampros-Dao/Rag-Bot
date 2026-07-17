"""
VeriTrace Backend – MCP Tool Server.

Exposes three blockchain-verification tools over the MCP stdio transport using FastMCP:
* ``check_duplicate``        – exact hash lookup
* ``get_verification_status`` – verification status by content ID
* ``get_similar_matches``     – fuzzy / perceptual-hash search
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
    check_duplicate as _check_duplicate,
    get_verification_status as _get_verification_status,
    get_similar_matches as _get_similar_matches,
)

mcp_server = FastMCP("veritrace-backend")

@mcp_server.tool()
def check_duplicate(file_hash: str) -> str:
    """Check whether an exact duplicate of *file_hash* exists on-chain.

    Parameters
    ----------
    file_hash : str
        The SHA-256 (or similar) hash of the file to look up.

    Returns
    -------
    str
        JSON-encoded result from the VeriTrace API.
    """
    result = _check_duplicate(file_hash)
    return json.dumps(result)

@mcp_server.tool()
def get_verification_status(content_id: str) -> str:
    """Return the verification status for a given *content_id*.

    Parameters
    ----------
    content_id : str
        The content identifier to query.

    Returns
    -------
    str
        JSON-encoded verification status.
    """
    result = _get_verification_status(content_id)
    return json.dumps(result)

@mcp_server.tool()
def get_similar_matches(content_id: str) -> str:
    """Find fuzzy / perceptual-hash matches for *content_id*.

    Parameters
    ----------
    content_id : str
        The perceptual hash or content identifier.

    Returns
    -------
    str
        JSON-encoded list of similar matches.
    """
    result = _get_similar_matches(content_id)
    return json.dumps(result)

if __name__ == "__main__":
    mcp_server.run()
