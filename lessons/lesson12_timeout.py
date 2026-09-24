from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class OrderState(TypedDict):
    order_id: str
    attempt_count: int
    status: str
    result: str

def get_order(order_id: str):
    print(f"Calling order service for {order_id}")
    raise TimeoutError("Order service timed out")

def retrieve_order(state: OrderState):
    attempt = state["attempt_count"] + 1

    print(f"Attempt {attempt}")

    try:
        result = get_order(state["order_id"])

        return {
            "attempt_count": attempt,
            "status": "success",
            "result": result,
        }

    except TimeoutError:
        return {
            "attempt_count": attempt,
            "status": "timeout",
            "result": "",
        }       

def route_after_retrieval(state: OrderState):
    if state["status"] == "success":
        return "done"

    if state["status"] == "timeout":
        if state["attempt_count"] < 3:
            return "retry"
        return "failed"

    return "failed"

def order_complete(state: OrderState):
    return {
        "status": "complete"
    }


def order_failed(state: OrderState):
    return {
        "status": "failed",
        "result": (
            "We're having trouble checking your order. "
            "Please try again later."
        ),
    }

builder = StateGraph(OrderState)

builder.add_node("retrieve_order", retrieve_order)
builder.add_node("order_complete", order_complete)
builder.add_node("order_failed", order_failed)

builder.add_edge(START, "retrieve_order")

builder.add_conditional_edges(
    "retrieve_order",
    route_after_retrieval,
    {
        "done": "order_complete",
        "retry": "retrieve_order",
        "failed": "order_failed",
    },
)

builder.add_edge("order_complete", END)
builder.add_edge("order_failed", END)

graph = builder.compile()

result = graph.invoke(
    {
        "order_id": "ORD-123",
        "attempt_count": 0,
        "status": "",
        "result": "",
    }
)

print("\n--- FINAL RESULT ---")
print(result)