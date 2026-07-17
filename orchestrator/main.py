import os
import sys
import asyncio
from typing import List
from contextlib import AsyncExitStack

# Ensure python can import rag from the root project directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.tools import tool
from dotenv import load_dotenv

from rag.retrieve import retrieve
from orchestrator.graph import create_graph

load_dotenv()

@tool
def retrieve_docs(query: str) -> str:
    """Retrieve relevant documentation for VeriTrace to answer user questions about deduplication, matching threshold, fingerprinting, etc."""
    results = retrieve(query, k=4)
    if not results:
        return "No relevant documentation found."
    return "\n\n".join([f"Source: {r['source']}\n{r['text']}" for r in results])

async def run_agent(message: str) -> str:
    # Set up stdio MCP client parameters
    backend_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp-backend/server.py"]
    )
    notify_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp-notify/server.py"]
    )

    async with AsyncExitStack() as stack:
        # Initialize Backend MCP
        backend_read, backend_write = await stack.enter_async_context(stdio_client(backend_params))
        backend_session = await stack.enter_async_context(ClientSession(backend_read, backend_write))
        await backend_session.initialize()
        backend_tools = await load_mcp_tools(backend_session)
        
        # Initialize Notify MCP
        notify_read, notify_write = await stack.enter_async_context(stdio_client(notify_params))
        notify_session = await stack.enter_async_context(ClientSession(notify_read, notify_write))
        await notify_session.initialize()
        notify_tools = await load_mcp_tools(notify_session)
        
        # Combine tools
        tools = [retrieve_docs] + backend_tools + notify_tools
        
        # Create graph
        graph = create_graph(tools)
        
        inputs = {"messages": [("user", message)]}
        result = await graph.ainvoke(inputs)
        
        return result["messages"][-1].content

if __name__ == "__main__":
    if len(sys.argv) > 1:
        msg = sys.argv[1]
    else:
        msg = "Hi, what is the pHash threshold?"
    
    response = asyncio.run(run_agent(msg))
    print(response)
