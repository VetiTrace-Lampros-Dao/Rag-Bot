# VeriTrace Help Bot

A RAG + MCP chatbot for VeriTrace, an open-source content provenance and forgery detection platform.

## Features
- **RAG (Retrieval-Augmented Generation):** Embeds and queries documentation about VeriTrace using Gemini `gemini-embedding-2` and ChromaDB.
- **MCP Backend Tools:** FastMCP server exposing `check_duplicate`, `get_verification_status`, and `get_similar_matches`.
- **MCP Notify Tools:** FastMCP server exposing `notify_discord` and `notify_slack`.
- **LangGraph Orchestrator:** Connects the LLM (`gemini-flash-latest`), RAG tools, and MCP servers into a cohesive agent.
- **FastAPI API:** Provides a standard `/chat` endpoint.
- **Dockerized:** Ready for deployment on Render.

## Setup

1. **Environment Variables:** Create a `.env` file with the following keys:
   ```env
   GEMINI_API_KEY=your_key
   DISCORD_WEBHOOK_URL=your_discord_webhook
   SLACK_WEBHOOK_URL=your_slack_webhook
   VERITRACE_API_BASE_URL=http://localhost:8080
   ```
2. **Ingest Documentation:**
   ```bash
   python rag/ingest.py --rebuild
   ```
3. **Run the API Server:**
   ```bash
   uvicorn api.main:app --port 8000
   ```
4. **Chat endpoint:**
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"message": "hi"}' http://localhost:8000/chat
   ```
   **Streaming chat endpoint (SSE):**
   ```bash
   curl -N -X POST -H "Content-Type: application/json" -H "Accept: text/event-stream" -d '{"message": "hi"}' "http://localhost:8000/chat?stream=true"
   ```

## Architecture
- `docs/` - Markdown documentation.
- `rag/` - Ingestion and retrieval logic.
- `mcp-backend/` - MCP Server for interacting with VeriTrace APIs.
- `mcp-notify/` - MCP Server for Slack/Discord notifications.
- `orchestrator/` - LangGraph logic defining agent state and nodes.
- `api/` - FastAPI wrapper and Dockerfile.
