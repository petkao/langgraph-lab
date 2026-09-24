from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.tools import tool
from typing import Annotated
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
# from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
# import psycopg
from psycopg_pool import ConnectionPool

load_dotenv()

llm = ChatOpenAI(model="gpt-5.4-mini")

class RefundAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

class ShippingAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

class CustomerServiceState(TypedDict):
    customer_message: str
    messages: Annotated[list[AnyMessage], add_messages]
    intent: str
    response: str

@tool
def get_refund_policy() -> str:
    """Retrieve the current refund policy."""
    return (
        "Customers may request a refund within 30 days of purchase "
        "if the product is returned in acceptable condition."
    )

@tool
def track_shipment(order_id: str) -> str:
    """Retrieve the current shipping status for an order."""
    print(f"Tracking shipment for {order_id}")

    return (
        f"Order {order_id} was shipped and is currently in transit. "
        f"Estimated delivery is tomorrow."
    )

refund_tools = [get_refund_policy]

refund_llm = llm.bind_tools(refund_tools)

shipping_tools = [track_shipment]

shipping_llm = llm.bind_tools(shipping_tools)

def call_refund_model(state: RefundAgentState):
    response = refund_llm.invoke(state["messages"])

    return {
        "messages": [response]
    }

def call_shipping_model(state: ShippingAgentState):
    response = shipping_llm.invoke(state["messages"])

    return {
        "messages": [response]
    }

refund_tool_node = ToolNode(refund_tools)

shipping_tool_node = ToolNode(shipping_tools)

def refund_agent(state: CustomerServiceState):
    refund_result = refund_graph.invoke({
        "messages": state["messages"]
    })

    final_message = refund_result["messages"][-1]

    return {
        "response": final_message.content,
        "messages": [final_message]
    }

def shipping_agent(state: CustomerServiceState):
    shipping_result = shipping_graph.invoke({
        "messages": state["messages"]
    })

    final_message = shipping_result["messages"][-1]

    return {
        "response": final_message.content,
        "messages": [final_message]
    }

def handle_unknown(state: CustomerServiceState):

    return {
        "response": (
            "I'm sorry, but I can only help with "
            "refund and shipping questions."
        )
    }

def route_refund_agent(state: RefundAgentState) -> str:
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return "end"

def route_shipping_agent(state: ShippingAgentState) -> str:
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return "end"

refund_builder = StateGraph(RefundAgentState)

refund_builder.add_node(
    "call_refund_model",
    call_refund_model
)

refund_builder.add_node(
    "refund_tools",
    refund_tool_node
)

refund_builder.add_edge(
    START,
    "call_refund_model"
)

refund_builder.add_edge(
    "refund_tools",
    "call_refund_model"
)

refund_builder.add_conditional_edges(
    "call_refund_model",
    route_refund_agent,
    {
        "tools": "refund_tools",
        "end": END,
    }
)

refund_graph = refund_builder.compile()

'''
refund_result = refund_graph.invoke({
    "messages": [
        HumanMessage(
            content=(
                "I bought a laptop yesterday and changed my mind. "
                "What is the refund policy?"
            )
        )
    ]
})
'''

shipping_builder = StateGraph(ShippingAgentState)

shipping_builder.add_node(
    "call_shipping_model",
    call_shipping_model
)

shipping_builder.add_node(
    "shipping_tools",
    shipping_tool_node
)

shipping_builder.add_edge(
    START,
    "call_shipping_model"
)

shipping_builder.add_edge(
    "shipping_tools",
    "call_shipping_model"
)

shipping_builder.add_conditional_edges(
    "call_shipping_model",
    route_shipping_agent,
    {
        "tools": "shipping_tools",
        "end": END,
    }
)

shipping_graph = shipping_builder.compile()

'''
print("\n--- REFUND GRAPH TEST ---")

for message in refund_result["messages"]:
    print("\nType:", type(message).__name__)
    print("Content:", message.content)

    if hasattr(message, "tool_calls"):
        print("Tool calls:", message.tool_calls)
'''

def add_customer_message(state: CustomerServiceState):
    return {
        "messages": [
            HumanMessage(content=state["customer_message"])
        ]
    }

def understand_intent(state: CustomerServiceState):

    result = llm.invoke(
        [
            {
                "role": "system",
                "content": (
                    "Classify the customer's latest request using the "
                    "conversation history when necessary. "
                    "Return exactly one word: refund, shipping, or unknown."
                ),
            },
            *state["messages"],
        ]
    )

    intent = result.content.strip().lower()

    return {
        "intent": intent
    }
def route_request(state: CustomerServiceState) -> str:
    if state["intent"] == "refund":
        return "refund"

    if state["intent"] == "shipping":
        return "shipping"

    return "unknown"

builder = StateGraph(CustomerServiceState)

builder.add_node("refund_agent", refund_agent)
builder.add_node("shipping_agent", shipping_agent)
builder.add_node("understand_intent", understand_intent)
builder.add_node("add_customer_message", add_customer_message)
builder.add_node("handle_unknown", handle_unknown)

builder.add_edge(START, "add_customer_message")
builder.add_edge("add_customer_message", "understand_intent")

builder.add_conditional_edges(
    "understand_intent",
    route_request,
    {
        "refund": "refund_agent",
        "shipping": "shipping_agent",
        "unknown": "handle_unknown",
    }
)

builder.add_edge("refund_agent", END)
builder.add_edge("shipping_agent", END)
builder.add_edge("handle_unknown", END)

DB_URI = "postgresql://tzechungkao@localhost:5432/langgraph_lab"

pool = ConnectionPool(
    conninfo=DB_URI,
    max_size=10,
    open=False,
    kwargs={
        "autocommit": True,
        "prepare_threshold": 0,
    },
)

checkpointer = PostgresSaver(pool)

customer_service_graph = builder.compile(
    checkpointer=checkpointer
)

