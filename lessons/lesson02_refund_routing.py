from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class RefundState(TypedDict):
    customer_name: str
    refund_amount: float
    status: str

def automatic_refund(state: RefundState):
    return {
        "status": "Refund approved automatically."
    }


def human_approval(state: RefundState):
    return {
        "status": "Refund requires human approval."
    }

def route_refund(state: RefundState):
    if state["refund_amount"] <= 500:
        return "automatic"

    return "human"

builder = StateGraph(RefundState)

builder.add_node("automatic_refund", automatic_refund)
builder.add_node("human_approval", human_approval)

builder.add_conditional_edges(
    START,
    route_refund,
    {
        "automatic": "automatic_refund",
        "human": "human_approval",
    }
)

builder.add_edge("automatic_refund", END)
builder.add_edge("human_approval", END)

graph = builder.compile()

result = graph.invoke({
    "customer_name": "Peter",
    "refund_amount": 700,
    "status": ""
})

print(result)

# poetry run python lessons/lesson02_refund_routing.py