"""
Lightweight agent for the web API deployment.
Uses the MCP tool functions directly as LangChain tools,
avoiding subprocess-based stdio MCP connections that fail in
containerized environments like Render.
"""
import os
import sys
import asyncio

# ── Environment setup (MUST happen before any LangChain imports) ──
from dotenv import load_dotenv
load_dotenv()

# Render sets GEMINI_API_KEY, but LangChain expects GOOGLE_API_KEY
if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from orchestrator.key_manager import key_manager
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

async def stream_web_agent(message: str):
    """Stream the agent response chunk by chunk."""
    response = await run_web_agent(message)
    yield response


def create_streaming_graph(tools, api_key):
    async def chatbot(state: MessagesState):
        llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", api_key=api_key, streaming=True, max_retries=5)
        llm_with_tools = llm.bind_tools(tools)
        response_msg = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response_msg]}

    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", ToolNode(tools=tools))
    
    graph_builder.add_edge(START, "chatbot")
    
    def route_tools(state: MessagesState):
        messages = state.get("messages", [])
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END
        
    graph_builder.add_conditional_edges("chatbot", route_tools, {"tools": "tools", END: END})
    graph_builder.add_edge("tools", "chatbot")
    
    return graph_builder.compile()

_streaming_graph_cache = {}

TOOL_DISPLAY_NAMES = {
    "retrieve_docs": "Searching knowledge base",
    "check_duplicate": "Checking for duplicates",
    "get_verification_status": "Checking verification status",
    "get_similar_matches": "Finding similar matches",
    "notify_discord": "Sending Discord notification",
    "notify_slack": "Sending Slack notification"
}

async def stream_web_agent_v2(message: str, cancel_event: asyncio.Event = None):
    tokens_sent = False
    backoff = 1.0
    max_attempts = len(key_manager.keys) * 2  # Allow cycling through keys twice with backoff
    
    for attempt in range(max_attempts):
        # Try to get a key that isn't on cooldown
        current_key = key_manager.get_available_key()
        
        if current_key is None:
            # All keys are on cooldown — wait for the soonest one to recover
            wait_time = key_manager.get_soonest_cooldown_remaining()
            if wait_time > 0 and attempt < max_attempts - 1:
                print(f"[STREAM_AGENT] All keys on cooldown. Waiting {wait_time:.1f}s for recovery...", file=sys.stderr)
                yield {"type": "status", "message": f"All keys busy. Retrying in {int(wait_time)+1}s..."}
                await asyncio.sleep(wait_time + 0.5)
                current_key = key_manager.get_api_key()
            else:
                break
        
        if current_key not in _streaming_graph_cache:
            _streaming_graph_cache[current_key] = create_streaming_graph(ALL_TOOLS, current_key)
            
        graph = _streaming_graph_cache[current_key]
        
        try:
            async for event in graph.astream_events({"messages": [("user", message)]}, version="v2"):
                if cancel_event and cancel_event.is_set():
                    yield {"type": "done", "reason": "cancelled"}
                    return
                
                kind = event["event"]
                
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and isinstance(chunk.content, str) and chunk.content:
                        tokens_sent = True
                        yield {"type": "token", "content": chunk.content}
                        
                elif kind == "on_tool_start":
                    name = event.get("name", "unknown")
                    display_name = TOOL_DISPLAY_NAMES.get(name, name)
                    yield {"type": "tool_start", "tool": display_name}
                    
                elif kind == "on_tool_end":
                    name = event.get("name", "unknown")
                    display_name = TOOL_DISPLAY_NAMES.get(name, name)
                    yield {"type": "tool_end", "tool": display_name}
            
            yield {"type": "done"}
            return
            
        except Exception as e:
            error_str = str(e).lower()
            if any(term in error_str for term in ["429", "quota", "resourceexhausted", "rate limit", "401", "unauthenticated", "permission", "denied", "403", "503", "unavailable"]):
                if tokens_sent:
                    yield {"type": "error", "message": "Rate limit or service error. Please try again in a moment."}
                    return
                else:
                    print(f"[STREAM_AGENT] API Key error (attempt {attempt+1}/{max_attempts}): {error_str[:80]}... Rotating.", file=sys.stderr)
                    key_manager.rotate_key(failed_key=current_key)
                    _streaming_graph_cache.pop(current_key, None)
                    # Exponential backoff before trying the next key
                    await asyncio.sleep(backoff)
                    backoff = min(8, backoff * 2)
                    continue
            else:
                yield {"type": "error", "message": str(e)}
                return
                
    yield {"type": "error", "message": "All API keys exhausted. Please try again in ~60 seconds."}
