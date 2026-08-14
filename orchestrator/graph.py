from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from orchestrator.key_manager import key_manager

load_dotenv()

def create_graph(tools: list):
    def chatbot(state: MessagesState):
        def _call_llm(active_key):
            llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", google_api_key=active_key, max_retries=5)
            llm_with_tools = llm.bind_tools(tools)
            return llm_with_tools.invoke(state["messages"])

        response_msg = key_manager.execute_with_rotation(_call_llm)
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


_compiled_graph = None

async def init_graph():
    global _compiled_graph
    from orchestrator.web_agent import ALL_TOOLS
    _compiled_graph = create_graph(ALL_TOOLS)
    return _compiled_graph

def run_turn(session_id: str, prompt: str) -> dict:
    global _compiled_graph
    if _compiled_graph is None:
        from orchestrator.web_agent import ALL_TOOLS
        _compiled_graph = create_graph(ALL_TOOLS)
    
    inputs = {"messages": [("user", prompt)]}
    result = _compiled_graph.invoke(inputs)
    reply = result["messages"][-1].content
    if isinstance(reply, list):
        text_parts = [b["text"] if isinstance(b, dict) and "text" in b else str(b) for b in reply]
        reply = "\n".join(text_parts)
    return {"reply": str(reply)}

