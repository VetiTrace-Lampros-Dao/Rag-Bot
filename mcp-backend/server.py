"""
VeriTrace Backend – MCP Tool Server.

Exposes three blockchain-verification tools over the MCP stdio transport:

* ``check_duplicate``        – exact hash lookup
* ``get_verification_status`` – verification status by content ID
* ``get_similar_matches``     – fuzzy / perceptual-hash search

Run directly:
    python mcp-backend/server.py
"""

from __future__ import annotations

import asyncio
import json
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server

# Import the raw helpers so all HTTP logic lives in one place.
from tools import (  # type: ignore[import-untyped]
    check_duplicate as _check_duplicate,
    get_verification_status as _get_verification_status,
    get_similar_matches as _get_similar_matches,
)

# ---------------------------------------------------------------------------
# MCP Server setup
# ---------------------------------------------------------------------------

server = Server("veritrace-backend")


@server.tool()
async def check_duplicate(file_hash: str) -> str:
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


@server.tool()
async def get_verification_status(content_id: str) -> str:
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


@server.tool()
async def get_similar_matches(content_id: str) -> str:
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


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

async def main() -> None:
    """Run the MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
