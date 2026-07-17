import os
import sys
import asyncio
import threading
import time
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from rag.retrieve import retrieve as rag_retrieve
from orchestrator.key_manager import key_manager

@tool
def retrieve_docs(query: str) -> str:
    """Search VeriTrace's internal documentation for how the system works
    (fingerprinting, dedup pipeline, matching thresholds, verify endpoint shape,
    source of truth). Use this for conceptual/how-it-works questions, not for
    looking up a specific file or content ID."""
    results = rag_retrieve(query, k=4)
    if not results:
        return "No relevant documentation found."
    return "\n\n".join(f"[{r['source']}] {r['text']}" for r in results)

# Global variables to store the compiled graph and client
graph = None
mcp_client = None

def run_async(coro):
    """Run an async coroutine from a synchronous context, even if an event loop is already running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        result = [None]
        exception = [None]
        def worker():
            try:
                # Create a new event loop for this thread to execute the coroutine
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result[0] = new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            except Exception as e:
                exception[0] = e
        t = threading.Thread(target=worker)
        t.start()
        t.join()
        if exception[0]:
            raise exception[0]
        return result[0]
    else:
        return asyncio.run(coro)

async def init_graph():
    global graph, mcp_client
    if graph is not None:
        return graph

    from langchain_mcp_adapters.client import MultiServerMCPClient

    backend_script = os.path.join(PROJECT_ROOT, "mcp-backend", "server.py")
    notify_script = os.path.join(PROJECT_ROOT, "mcp-notify", "server.py")

    mcp_client = MultiServerMCPClient({
        "backend": {
            "command": sys.executable,
            "args": [backend_script],
            "transport": "stdio",
        },
        "notify": {
            "command": sys.executable,
            "args": [notify_script],
            "transport": "stdio",
        },
    })
    
    mcp_tools = await mcp_client.get_tools()
    all_tools = [retrieve_docs] + mcp_tools

    model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

    def get_llm_with_tools():
        api_key = key_manager.get_api_key()
        llm = ChatGoogleGenerativeAI(model=model_name, api_key=api_key, max_retries=0, temperature=0)
        return llm.bind_tools(all_tools)

    def agent_node(state: MessagesState):
        max_retries = max(10, len(key_manager.keys) * 2)
        backoff = 1
        
        for attempt in range(max_retries):
            current_key = key_manager.get_api_key()
            try:
                llm_with_tools = get_llm_with_tools()
                response = llm_with_tools.invoke(state["messages"])
                return {"messages": [response]}
            except Exception as e:
                err_msg = str(e)
                if any(x in err_msg.upper() for x in ["429", "RESOURCE_EXHAUSTED", "401", "UNAUTHENTICATED", "403", "PERMISSION_DENIED", "503", "UNAVAILABLE", "500", "INTERNAL"]):
                    print(f"\n[ORCHESTRATOR] Quota/Auth/API error ({err_msg[:60]}...). Rotating API key away from index {key_manager.current_index}...", file=sys.stderr)
                    key_manager.rotate_key(current_key)
                    time.sleep(backoff)
                    backoff = min(8, backoff * 1.5)  # exponential backoff capped at 8s
                else:
                    raise e
                    
        # Final fallback attempt
        llm_with_tools = get_llm_with_tools()
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: MessagesState):
        last_message = state["messages"][-1]
        return "tools" if getattr(last_message, "tool_calls", None) else END

    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("agent", agent_node)
    graph_builder.add_node("tools", ToolNode(all_tools))
    graph_builder.set_entry_point("agent")
    graph_builder.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph_builder.add_edge("tools", "agent")

    checkpointer = MemorySaver()
    graph = graph_builder.compile(checkpointer=checkpointer)
    return graph

def run_turn(session_id: str, user_message: str) -> dict:
    global graph
    if graph is None:
        graph = run_async(init_graph())

    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": 20,
    }
    
    result = run_async(
        graph.ainvoke({"messages": [("user", user_message)]}, config=config)
    )
        
    final_message = result["messages"][-1]
    return {"reply": final_message.content}
