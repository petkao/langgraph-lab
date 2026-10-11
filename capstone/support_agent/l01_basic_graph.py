
from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class SupportState(TypedDict):
    customer_message: str
    intent: str
    status: str

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

builder = StateGraph(SupportState)

builder.add_node("receive_request", receive_request)
builder.add_node("understand_request", understand_request)

builder.add_edge(START, "receive_request")
builder.add_edge("receive_request", "understand_request")
builder.add_edge("understand_request", END)

graph = builder.compile()


initial_state = {
    "customer_message": "My laptop arrived damaged. Can I get a replacement?",
    "intent": "",
    "status": ""
}

result = graph.invoke(initial_state)

print("\nFinal State:")
print(result)

# poetry run python l01_basic_graph.py 




