from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class RefundState(TypedDict):
    amount: float
    status: str

def evaluate_refund(state: RefundState):

    if state["amount"] <= 500:
        return {
            "status": "automatic"
        }

    return {
        "status": "human_approval"
    }

def route_refund(state: RefundState):

    if state["status"] == "automatic":
        return "automatic"

    if state["status"] == "human_approval":
        return "human"

    return "invalid"

def automatic_refund(state: RefundState):
    return {
        "status": "completed_automatically"
    }


def human_approval(state: RefundState):
    return {
        "status": "waiting_for_human"
    }


def invalid_refund(state: RefundState):
    return {
        "status": "invalid"
    }

builder = StateGraph(RefundState)

builder.add_node(
    "evaluate_refund",
    evaluate_refund
)

builder.add_node(
    "automatic_refund",
    automatic_refund
)

builder.add_node(
    "human_approval",
    human_approval
)

builder.add_node(
    "invalid_refund",
    invalid_refund
)

builder.add_edge(
    START,
    "evaluate_refund"
)


builder.add_conditional_edges(
    "evaluate_refund",
    route_refund,
    {
        "automatic": "automatic_refund",
        "human": "human_approval",
        "invalid": "invalid_refund",
    }
)


builder.add_edge("automatic_refund", END)
builder.add_edge("human_approval", END)
builder.add_edge("invalid_refund", END)

graph = builder.compile()

def test_small_refund_graph():

    result = graph.invoke(
        {
            "amount": 200,
            "status": ""
        }
    )

    assert result["status"] == "completed_automatically"


def test_large_refund_graph():

    result = graph.invoke(
        {
            "amount": 1200,
            "status": ""
        }
    )

    assert result["status"] == "waiting_for_human"

test_small_refund_graph()
test_large_refund_graph()

print("All graph tests passed.")

# poetry run python -m lessons.lesson16_graph_testing