from langchain_core.messages import HumanMessage
from typing import TypedDict, Annotated

from langchain_core.messages import AnyMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

@tool
def get_order(order_id: str) -> str:
    """Retrieve order information for an order ID."""

    print(f"Looking up order: {order_id}")

    return (
        f"Order {order_id} has an amount of $300.00 "
        f"and status delivered."
    )    

llm = ChatOpenAI(model="gpt-5.4-mini")

tools = [get_order]

llm_with_tools = llm.bind_tools(tools)

def call_model(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])

    return {
        "messages": [response]
    }

builder = StateGraph(AgentState)

tool_node = ToolNode(tools)

def route_after_model(state: AgentState):
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return "end"

builder.add_node("call_model", call_model)
builder.add_node("tools", tool_node)

builder.add_edge(START, "call_model")

builder.add_conditional_edges(
    "call_model",
    route_after_model,
    {
        "tools": "tools",
        "end": END,
    }
)

builder.add_edge("tools", "call_model")

graph = builder.compile()

result = graph.invoke({
    "messages": [
        HumanMessage(
            # content="What is the status of order ORD-123?"
            content="What is the weather today?"
        )
    ]
})

for i, message in enumerate(result["messages"]):
    print(f"\nMessage {i}")
    print("Type:", type(message).__name__)
    print("Content:", message.content)

    if hasattr(message, "tool_calls"):
        print("Tool calls:", message.tool_calls)

