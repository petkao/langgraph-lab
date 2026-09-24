from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class CustomerServiceState(TypedDict):
    customer_message: str
    intent: str
    response: str

def refund_agent(state: CustomerServiceState):
    return {
        "response": "The Refund Agent is handling your request."
    }


def shipping_agent(state: CustomerServiceState):
    return {
        "response": "The Shipping Agent is handling your request."
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

result = customer_service_graph.invoke({
    "customer_message": "I want my money back.",
    "intent": "shipping",
    "response": ""
})

print(result)

