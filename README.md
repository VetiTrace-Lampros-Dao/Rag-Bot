# VeriTrace Help Bot

A RAG + MCP chatbot for the VeriTrace content provenance platform. Answers questions about how the system works (grounded in real docs), calls the live backend to check specific content, and sends Discord/Slack notifications on request.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy .env.example to .env and fill in your secrets
cp .env.example .env

# 3. Verify config
python check_config.py

# 4. Ingest docs into the vector store
python rag/ingest.py

# 5. Start the chatbot
python orchestrator/main.py
```

## Architecture

- **`rag/`** — Retrieval-Augmented Generation: doc ingestion, embedding, retrieval, and grounded answering
- **`mcp-backend/`** — MCP tool server for VeriTrace API calls (verify exact, verify fuzzy, etc.)
- **`mcp-notify/`** — MCP tool server for Discord and Slack webhook notifications
- **`orchestrator/`** — Gemini-powered chat loop with function calling across all tools
- **`docs/`** — Source markdown documents for the RAG knowledge base

## Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | API key for Google Gemini |
| `DISCORD_WEBHOOK_URL` | Discord incoming webhook URL |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL |
| `VERITRACE_API_BASE_URL` | Base URL for the VeriTrace backend API |
