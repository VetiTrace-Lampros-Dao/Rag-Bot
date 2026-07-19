"""
Lightweight agent for the web API deployment.
Uses the MCP tool functions directly as LangChain tools,
avoiding subprocess-based stdio MCP connections that fail in
containerized environments like Render.
"""
import os
import sys

# ── Environment setup (MUST happen before any LangChain imports) ──
from dotenv import load_dotenv
load_dotenv()

# Render sets GEMINI_API_KEY, but LangChain expects GOOGLE_API_KEY
if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from langchain_core.tools import tool
from rag.retrieve import retrieve
from orchestrator.graph import create_graph

# ── RAG Tool ──────────────────────────────────────────────
@tool
def retrieve_docs(query: str) -> str:
    """Retrieve relevant documentation for VeriTrace to answer user questions about deduplication, matching threshold, fingerprinting, ArbiLearn, Web3 concepts, etc."""
    results = retrieve(query, k=4)
    if not results:
        return "No relevant documentation found."
    return "\n\n".join([f"Source: {r['source']}\n{r['text']}" for r in results])

# ── Backend Tools (direct function calls, no MCP subprocess) ──
def _get_base_url() -> str:
    return os.environ.get("VERITRACE_API_BASE_URL", "http://localhost:8080").rstrip("/")

@tool
def check_duplicate(sha256_hash: str) -> str:
    """Check if an exact duplicate exists using its SHA-256 hash."""
    base_url = _get_base_url()
    try:
        response = requests.get(f"{base_url}/api/v1/fingerprint/{sha256_hash}")
        if response.status_code == 200:
            return f"Match found! Fingerprint: {response.json()}"
        elif response.status_code == 404:
            return "No exact match found."
        else:
            return f"Error connecting to backend API: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error connecting to VeriTrace backend: {str(e)}"

@tool
def get_verification_status(asset_id: str) -> str:
    """Get the verification status and confidence score of an asset by its ID."""
    base_url = _get_base_url()
    try:
        response = requests.get(f"{base_url}/api/v1/assets/{asset_id}/verify")
        if response.status_code == 200:
            data = response.json()
            return f"Status: {data.get('status', 'Unknown')}, Confidence: {data.get('confidence', 'N/A')}"
        elif response.status_code == 404:
            return "Asset not found."
        else:
            return f"Error connecting to backend API: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error connecting to VeriTrace backend: {str(e)}"

@tool
def get_similar_matches(phash: str, threshold: int = 40) -> str:
    """Find visually similar matches using a perceptual hash and a Hamming distance threshold."""
    base_url = _get_base_url()
    try:
        response = requests.get(
            f"{base_url}/api/v1/fingerprint/similar",
            params={"phash": phash, "threshold": threshold}
        )
        if response.status_code == 200:
            return f"Similar matches: {response.json()}"
        elif response.status_code == 404:
            return "No similar matches found within threshold."
        else:
            return f"Error connecting to backend API: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error connecting to VeriTrace backend: {str(e)}"

# ── Notification Tools ────────────────────────────────────
@tool
def notify_discord(message: str) -> str:
    """Send a notification message to the Discord channel."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return "Discord notification failed: DISCORD_WEBHOOK_URL is not set."
    try:
        response = requests.post(webhook_url, json={"content": message})
        response.raise_for_status()
        return "Discord notification sent"
    except requests.exceptions.RequestException as e:
        return f"Discord notification failed: {str(e)}"

@tool
def notify_slack(message: str) -> str:
    """Send a notification message to the Slack channel."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return "Slack notification failed: SLACK_WEBHOOK_URL is not set."
    try:
        response = requests.post(webhook_url, json={"text": message})
        response.raise_for_status()
        return "Slack notification sent"
    except requests.exceptions.RequestException as e:
        return f"Slack notification failed: {str(e)}"

# ── All available tools ───────────────────────────────────
ALL_TOOLS = [
    retrieve_docs,
    check_duplicate,
    get_verification_status,
    get_similar_matches,
    notify_discord,
    notify_slack,
]

# ── Lazy graph initialization ─────────────────────────────
_graph = None

def _get_graph():
    global _graph
    if _graph is None:
        _graph = create_graph(ALL_TOOLS)
    return _graph

async def run_web_agent(message: str) -> str:
    """Run the agent without MCP subprocess overhead."""
    graph = _get_graph()
    inputs = {"messages": [("user", message)]}
    result = await graph.ainvoke(inputs)
    content = result["messages"][-1].content

    # Gemini can return content as a list of blocks like:
    # [{'type': 'text', 'text': '...', 'extras': {...}}]
    # We need to extract just the text string.
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                text_parts.append(block["text"])
            elif isinstance(block, str):
                text_parts.append(block)
        return "\n".join(text_parts) if text_parts else str(content)

    return content
