
from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class SupportState(TypedDict):
    customer_message: str
    intent: str
    status: str
    response: str

def receive_request(state: SupportState):
    print(f"Customer: {state["customer_message"]}")

    return {
        "status": "request_received"
    }

def understand_request(state: SupportState):
    message = state["customer_message"].lower()

    if "replacement" in message or "damage" in message:
        intent = "replacement"
    elif "refund" in message:
        intent = "refund"
    else:
        intent = "general_support"

    return {"intent" : intent,
            "status": "request_understand"
        }

def replacement_agent(state: SupportState):
    return {
        "response": "Let me check whether this order is eligible for replacement.",
        "status": "replacement_agent"
    }

def refund_agent(state: SupportState):
    return {
        "response": "Let me check whether this order is eligible for a refund.",
        "status": "refund_agent"
    }

def general_support_agent(state: SupportState):
    return {
        "response": "Let me help you with your support question.",
        "status": "general_support_agent"
    }

def route_by_intent(state: SupportState):
    return state["intent"]



builder = StateGraph(SupportState)

builder.add_node("receive_request", receive_request)
builder.add_node("understand_request", understand_request)
builder.add_node("general_support_agent", general_support_agent)
builder.add_node("replacement_agent",replacement_agent)
builder.add_node("refund_agent", refund_agent)


builder.add_edge(START, "receive_request")
builder.add_edge("receive_request", "understand_request")
builder.add_conditional_edges(
    "understand_request",
    route_by_intent,
    {
        "replacement": "replacement_agent",
        "refund": "refund_agent",
        "general_support": "general_support_agent",
    }
)

builder.add_edge("replacement_agent", END)
builder.add_edge("refund_agent", END)
builder.add_edge("general_support_agent", END)


graph = builder.compile()


initial_state = {
    # "customer_message": "My laptop arrived damaged. Can I get a replacement?",
    # "customer_message": "I want a refund for my laptop.",
    # "customer_message": "How do I reset my laptop password?",
    "customer_message": "The computer I received yesterday won't turn on. Please send me another one.",
    "intent": "",
    "status": ""
}

result = graph.invoke(initial_state)

print("\nFinal State:")
print(result)

# poetry run python l02_conditional_routing.py






