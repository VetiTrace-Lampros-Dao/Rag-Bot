"""VeriTrace Help Bot — Full Gemini Orchestrator

Integrates RAG retrieval with MCP backend and notification tools via
Gemini function calling. Maintains conversation history across turns.

Usage:
    python orchestrator/main.py
"""

import os
import sys
import time
import json
import traceback

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Add project root to path so imports work
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from rag.retrieve import retrieve as rag_retrieve
from rag.answer import format_context

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
TOOL_TIMEOUT = 15  # seconds


# ---------------------------------------------------------------------------
# Tool implementations (direct function calls, no MCP protocol needed)
# ---------------------------------------------------------------------------

def _backend_request(endpoint: str, params: dict) -> dict:
    """Make a request to the VeriTrace backend API with timeout handling."""
    import requests as req_lib
    base_url = os.getenv("VERITRACE_API_BASE_URL", "http://localhost:8080").rstrip("/")
    url = f"{base_url}{endpoint}"
    try:
        resp = req_lib.get(url, params=params, timeout=TOOL_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except req_lib.exceptions.ConnectionError as e:
        return {"error": "backend_unreachable", "message": f"Could not connect to VeriTrace backend at {base_url}: {e}"}
    except req_lib.exceptions.Timeout:
        return {"error": "backend_timeout", "message": f"Request to {url} timed out after {TOOL_TIMEOUT}s"}
    except req_lib.exceptions.HTTPError as e:
        return {"error": "backend_http_error", "message": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": "backend_error", "message": str(e)}


def tool_search_docs(query: str, num_results: int = 4) -> dict:
    """Search the VeriTrace knowledge base for relevant documentation."""
    try:
        results = rag_retrieve(query, k=num_results)
        if not results:
            return {"found": False, "message": "No relevant documentation found."}
        return {
            "found": True,
            "chunks": [{"text": r["text"], "source": r["source"]} for r in results],
        }
    except Exception as e:
        return {"error": "rag_error", "message": str(e)}


def tool_check_duplicate(file_hash: str) -> dict:
    """Check if a file (by SHA-256 hash) is a known duplicate in VeriTrace."""
    return _backend_request("/api/v1/verify/exact", {"hash": file_hash})


def tool_get_verification_status(content_id: str) -> dict:
    """Get the verification status of content by its SHA-256 hash."""
    return _backend_request("/api/v1/verify/exact", {"hash": content_id})


def tool_get_similar_matches(phash: str) -> dict:
    """Find visually similar content by perceptual hash (pHash) value."""
    return _backend_request("/api/v1/verify/fuzzy", {"phash": phash})


def tool_notify_discord(message: str) -> dict:
    """Send a notification message to the team's Discord channel."""
    import requests as req_lib
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return {"success": False, "error": "DISCORD_WEBHOOK_URL not configured"}
    try:
        resp = req_lib.post(
            webhook_url,
            json={"content": message},
            headers={"Content-Type": "application/json"},
            timeout=TOOL_TIMEOUT,
        )
        if resp.status_code in (200, 204):
            return {"success": True}
        return {"success": False, "error": f"Discord returned HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_notify_slack(message: str) -> dict:
    """Send a notification message to the team's Slack channel."""
    import requests as req_lib
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return {"success": False, "error": "SLACK_WEBHOOK_URL not configured"}
    try:
        resp = req_lib.post(
            webhook_url,
            json={"text": message},
            headers={"Content-Type": "application/json"},
            timeout=TOOL_TIMEOUT,
        )
        if resp.status_code == 200:
            return {"success": True}
        return {"success": False, "error": f"Slack returned HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Tool registry mapping tool names -> callables
# ---------------------------------------------------------------------------

TOOL_FUNCTIONS = {
    "search_docs": tool_search_docs,
    "check_duplicate": tool_check_duplicate,
    "get_verification_status": tool_get_verification_status,
    "get_similar_matches": tool_get_similar_matches,
    "notify_discord": tool_notify_discord,
    "notify_slack": tool_notify_slack,
}


# ---------------------------------------------------------------------------
# Gemini function declarations
# ---------------------------------------------------------------------------

TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="search_docs",
        description="Search the VeriTrace knowledge base and documentation for information about how the system works, including fingerprinting, deduplication, verification endpoints, matching thresholds, and architecture. Use this when the user asks conceptual or 'how does X work' questions.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "query": types.Schema(type="STRING", description="The search query to find relevant documentation"),
                "num_results": types.Schema(type="INTEGER", description="Number of results to return (default 4)"),
            },
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="check_duplicate",
        description="Check if a specific file is a known duplicate in the VeriTrace system by its SHA-256 hash. Use this when the user asks about a specific file hash being duplicated or flagged.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "file_hash": types.Schema(type="STRING", description="The SHA-256 hash of the file to check (e.g., '0x6ca0f85e...')"),
            },
            required=["file_hash"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_verification_status",
        description="Get the full verification status and metadata of content by its SHA-256 hash. Use this when the user asks about a specific content's registration status, creator, or on-chain verification.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "content_id": types.Schema(type="STRING", description="The SHA-256 hash of the content to verify"),
            },
            required=["content_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_similar_matches",
        description="Find visually similar content by perceptual hash (pHash) value. Use this when the user asks about finding similar images/videos or fuzzy matching.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "phash": types.Schema(type="STRING", description="The 64-bit perceptual hash value as a string (e.g., '9876543210123')"),
            },
            required=["phash"],
        ),
    ),
    types.FunctionDeclaration(
        name="notify_discord",
        description="Send a notification message to the team's Discord channel. Use this when the user asks to notify, alert, or inform the team about something via Discord.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "message": types.Schema(type="STRING", description="The notification message to send"),
            },
            required=["message"],
        ),
    ),
    types.FunctionDeclaration(
        name="notify_slack",
        description="Send a notification message to the team's Slack channel. Use this when the user asks to notify, alert, or inform the team about something via Slack.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "message": types.Schema(type="STRING", description="The notification message to send"),
            },
            required=["message"],
        ),
    ),
]


SYSTEM_INSTRUCTION = """You are the VeriTrace Help Bot, an intelligent assistant for the VeriTrace content provenance and forgery detection platform.

Your capabilities:
1. **Knowledge Base Search** — You can search internal documentation about how VeriTrace works (fingerprinting, deduplication, verification, thresholds, architecture). Always use `search_docs` for conceptual/architectural questions.
2. **Duplicate Check** — You can check if a specific file (by SHA-256 hash) is flagged as a duplicate.
3. **Verification Status** — You can look up the full verification record of registered content.
4. **Similar Content Search** — You can search for visually similar content using perceptual hash values.
5. **Team Notifications** — You can send messages to the team's Discord or Slack channels.

Guidelines:
- For "how does X work" questions, ALWAYS use search_docs first to ground your answer in real documentation. Never make up technical details.
- For questions about specific content (hashes, IDs), use the appropriate backend tool.
- When asked to notify or alert the team, use notify_discord or notify_slack (prefer Discord unless the user specifies Slack).
- If a backend tool returns an error (e.g., backend unreachable), tell the user clearly what happened and suggest they check the backend service.
- Maintain context from previous messages in the conversation. If the user says "that one" or "the last file", refer to earlier context.
- Be concise but thorough. Use bullet points for multi-part answers.
- Never claim VeriTrace can detect AI-generated content — it does visual similarity matching and provenance tracking only.
"""


# ---------------------------------------------------------------------------
# Gemini API call with exponential backoff retry
# ---------------------------------------------------------------------------

def call_gemini_with_retry(client, model: str, contents, config):
    """Call Gemini API with exponential backoff on 429 errors."""
    backoff = INITIAL_BACKOFF
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            return response
        except Exception as e:
            error_str = str(e)
            if any(term in error_str for term in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"]):
                if attempt < MAX_RETRIES - 1:
                    print(f"  [Rate limited or server busy, retrying in {backoff}s... (attempt {attempt + 1}/{MAX_RETRIES})]")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
            raise
    return None


# ---------------------------------------------------------------------------
# Execute a tool call from Gemini
# ---------------------------------------------------------------------------

def execute_tool_call(function_call) -> dict:
    """Execute a Gemini function call and return the result."""
    name = function_call.name
    args = dict(function_call.args) if function_call.args else {}

    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return {"error": "unknown_tool", "message": f"No tool named '{name}'"}

    try:
        result = func(**args)
        return result
    except Exception as e:
        return {"error": "tool_execution_error", "message": f"Tool '{name}' failed: {e}"}


# ---------------------------------------------------------------------------
# Main chat loop
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  VeriTrace Help Bot")
    print("  Powered by Gemini + RAG + MCP")
    print("=" * 60)
    print()
    print("Ask me about VeriTrace, check content status, or send notifications.")
    print("Type 'quit' or 'exit' to end the session.\n")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    model = DEFAULT_MODEL

    # Conversation history as Gemini Content objects
    history = []

    tools = types.Tool(function_declarations=TOOL_DECLARATIONS)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        # Add user message to history
        history.append(types.Content(role="user", parts=[types.Part(text=user_input)]))

        # Send to Gemini with tools
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[tools],
            temperature=0.3,
        )

        try:
            response = call_gemini_with_retry(client, model, history, config)
        except Exception as e:
            error_msg = f"I encountered an error communicating with Gemini: {e}"
            print(f"\nBot: {error_msg}")
            history.append(types.Content(role="model", parts=[types.Part(text=error_msg)]))
            continue

        if not response or not response.candidates:
            fallback = "I'm sorry, I didn't get a valid response. Please try again."
            print(f"\nBot: {fallback}")
            history.append(types.Content(role="model", parts=[types.Part(text=fallback)]))
            continue

        # Process the response — handle tool calls iteratively
        current_response = response
        max_tool_rounds = 5
        tool_round = 0

        while tool_round < max_tool_rounds:
            tool_round += 1
            candidate = current_response.candidates[0]
            content = candidate.content

            # Check if there are function calls
            function_calls = [p.function_call for p in (content.parts or []) if p.function_call]

            if not function_calls:
                # No tool calls — extract text and we're done
                break

            # Add model's tool-call response to history
            history.append(content)

            # Execute each function call
            tool_response_parts = []
            for fc in function_calls:
                print(f"  [Calling tool: {fc.name}({dict(fc.args) if fc.args else {}})]")
                result = execute_tool_call(fc)

                # If it's a search_docs result with chunks, format nicely
                if fc.name == "search_docs" and isinstance(result, dict) and result.get("found"):
                    result_for_model = result
                else:
                    result_for_model = result

                tool_response_parts.append(
                    types.Part(function_response=types.FunctionResponse(
                        name=fc.name,
                        response=result_for_model,
                    ))
                )

            # Add tool results to history
            history.append(types.Content(role="user", parts=tool_response_parts))

            # Send back to Gemini for the next round
            try:
                current_response = call_gemini_with_retry(client, model, history, config)
            except Exception as e:
                error_msg = f"I encountered an error after executing tools: {e}"
                print(f"\nBot: {error_msg}")
                history.append(types.Content(role="model", parts=[types.Part(text=error_msg)]))
                break

            if not current_response or not current_response.candidates:
                fallback = "I'm sorry, I lost track of the conversation. Please try again."
                print(f"\nBot: {fallback}")
                history.append(types.Content(role="model", parts=[types.Part(text=fallback)]))
                break

        # Extract final text response
        final_candidate = current_response.candidates[0]
        final_content = final_candidate.content
        text_parts = [p.text for p in (final_content.parts or []) if p.text]

        if text_parts:
            answer_text = "\n".join(text_parts)
            print(f"\nBot: {answer_text}")
            history.append(types.Content(role="model", parts=[types.Part(text=answer_text)]))
        elif not function_calls:
            # No text and no function calls
            fallback = "I processed the request but have nothing further to add."
            print(f"\nBot: {fallback}")
            history.append(types.Content(role="model", parts=[types.Part(text=fallback)]))


if __name__ == "__main__":
    main()
