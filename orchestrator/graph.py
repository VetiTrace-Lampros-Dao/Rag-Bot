from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

def create_graph(tools: list):
    # Initialize the LLM (Gemini Flash)
    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest")
    llm_with_tools = llm.bind_tools(tools)
    
    def chatbot(state: MessagesState):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}
        
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
