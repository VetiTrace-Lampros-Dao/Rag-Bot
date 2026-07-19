from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
import json
import logging
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from orchestrator.web_agent import run_web_agent, stream_web_agent

app = FastAPI(title="VeriTrace Help Bot API")
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Redirect root to the chat UI."""
    return RedirectResponse(url="/ui/")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/debug")
async def debug():
    """Diagnostic endpoint to check deployment health."""
    info = {}
    # Check env vars
    info["GOOGLE_API_KEY_set"] = bool(os.environ.get("GOOGLE_API_KEY"))
    info["GEMINI_API_KEY_set"] = bool(os.environ.get("GEMINI_API_KEY"))
    # Check chroma_db
    info["chroma_db_exists"] = os.path.exists("chroma_db")
    info["chroma_db_contents"] = os.listdir("chroma_db") if os.path.exists("chroma_db") else []
    info["cwd"] = os.getcwd()
    # Try retrieve
    try:
        from rag.retrieve import retrieve
        results = retrieve("test", k=1)
        info["retrieve_ok"] = True
        info["retrieve_count"] = len(results)
    except Exception as e:
        info["retrieve_ok"] = False
        info["retrieve_error"] = str(e)
    # Try graph
    try:
        from orchestrator.web_agent import _get_graph
        _get_graph()
        info["graph_ok"] = True
    except Exception as e:
        info["graph_ok"] = False
        info["graph_error"] = str(e)
    return info

# Mount the static directory to serve the UI
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="static")

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

def _wants_stream(request: Request) -> bool:
    if request.query_params.get("stream", "").lower() == "true":
        return True
    accept = request.headers.get("accept", "").lower()
    return "text/event-stream" in accept

@app.post("/chat")
async def chat(request: Request, payload: ChatRequest):
    try:
        if _wants_stream(request):
            async def event_stream():
                try:
                    async for chunk in stream_web_agent(payload.message):
                        data = json.dumps({"type": "chunk", "content": chunk})
                        yield f"data: {data}\n\n"
                    done = json.dumps({"type": "done"})
                    yield f"data: {done}\n\n"
                except Exception as e:
                    logger.exception("Streaming chat failed")
                    error = json.dumps({"type": "error", "message": f"{type(e).__name__}: {str(e)}"})
                    yield f"data: {error}\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        response_text = await run_web_agent(payload.message)
        return ChatResponse(response=response_text)
    except Exception as e:
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")
