from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.tools import tool
from typing import Annotated
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv()

llm = ChatOpenAI(model="gpt-5.4-mini")

class RefundAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

class ShippingAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

class CustomerServiceState(TypedDict):
    customer_message: str
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
    customer_message = state["customer_message"]

    refund_result = refund_graph.invoke({
        "messages": [
            HumanMessage(content=customer_message)
        ]
    })

    final_message = refund_result["messages"][-1]

    return {
        "response": final_message.content
    }

def shipping_agent(state: CustomerServiceState):
    customer_message = state["customer_message"]

    shipping_result = shipping_graph.invoke({
        "messages": [
            HumanMessage(content=customer_message)
        ]
    })

    final_message = shipping_result["messages"][-1]

    return {
        "response": final_message.content
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

def route_request(state: CustomerServiceState) -> str:
    if state["intent"] == "refund":
        return "refund"

    if state["intent"] == "shipping":
        return "shipping"

    return "unknown"

builder = StateGraph(CustomerServiceState)

builder.add_node("refund_agent", refund_agent)
builder.add_node("shipping_agent", shipping_agent)

builder.add_conditional_edges(
    START,
    route_request,
    {
        "refund": "refund_agent",
        "shipping": "shipping_agent",
        "unknown": END,
    }
)

builder.add_edge("refund_agent", END)
builder.add_edge("shipping_agent", END)

customer_service_graph = builder.compile()

'''
result = customer_service_graph.invoke({
    "customer_message":
        "I bought a laptop yesterday. What is the refund policy?",
    "intent": "refund",
    "response": ""
})


print("\n--- CUSTOMER SERVICE GRAPH TEST ---")
print(result)
'''

'''
result = customer_service_graph.invoke({
    "customer_message":
        "My package hasn't arrived yet. Can you tell me where it is?",
    "intent": "shipping",
    "response": ""
})

print(result)
'''

'''
shipping_result = shipping_graph.invoke({
    "messages": [
        HumanMessage(
            content="Where is order ORD-123?"
        )
    ]
})

print("\n--- SHIPPING GRAPH TEST ---")

for message in shipping_result["messages"]:
    print("\nType:", type(message).__name__)
    print("Content:", message.content)

    if hasattr(message, "tool_calls"):
        print("Tool calls:", message.tool_calls)
'''

'''
result = customer_service_graph.invoke({
    "customer_message": "Where is order ORD-123?",
    "intent": "shipping",
    "response": ""
})

print("\n--- CUSTOMER SERVICE SHIPPING TEST ---")
print(result)
'''

result = customer_service_graph.invoke({
    "customer_message":
        "I bought a laptop yesterday. What is the refund policy?",
    "intent": "refund",
    "response": ""
})

print("\n--- CUSTOMER SERVICE REFUND TEST ---")
print(result)

# poetry run python lessons/lesson09d_multi_agent.py