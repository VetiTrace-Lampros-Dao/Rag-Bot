from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from orchestrator.web_agent import run_web_agent, stream_web_agent

app = FastAPI(title="VeriTrace Help Bot API")

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
    return RedirectResponse(url="/ui")

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
                except Exception as exc:
                    error = json.dumps({"type": "error", "message": str(exc)})
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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
