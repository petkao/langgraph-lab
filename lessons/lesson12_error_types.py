from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class OrderState(TypedDict):
    order_id: str
    attempt_count: int
    status: str
    result: str

class OrderNotFoundError(Exception):
    pass

def get_order(order_id: str):
    print(f"Calling order service for {order_id}")

    if order_id == "BAD-999":
        raise OrderNotFoundError(
            f"Order {order_id} was not found"
        )

    return {
        "order_id": order_id,
        "status": "shipped",
    }

def retrieve_order(state: OrderState):
    attempt = state["attempt_count"] + 1

    print(f"Attempt {attempt}")

    try:
        order = get_order(state["order_id"])

        return {
            "attempt_count": attempt,
            "status": "success",
            "result": f"Order status: {order['status']}",
        }

    except OrderNotFoundError:
        return {
            "attempt_count": attempt,
            "status": "not_found",
            "result": "We couldn't find that order.",
        }

def route_after_retrieval(state: OrderState):
    if state["status"] == "success":
        return "done"

    if state["status"] == "not_found":
        return "not_found"

    return "failed"

def order_complete(state: OrderState):
    return {
        "status": "complete"
    }

def order_not_found(state: OrderState):
    return {
        "status": "not_found"
    }


def order_failed(state: OrderState):
    return {
        "status": "failed",
        "result": "We couldn't check your order. Please try again later."
    }

builder = StateGraph(OrderState)

builder.add_node("retrieve_order", retrieve_order)
builder.add_node("order_complete", order_complete)
builder.add_node("order_not_found", order_not_found)
builder.add_node("order_failed", order_failed)

builder.add_edge(START, "retrieve_order")

builder.add_conditional_edges(
    "retrieve_order",
    route_after_retrieval,
    {
        "done": "order_complete",
        "not_found": "order_not_found",
        "failed": "order_failed",
    },
)

builder.add_edge("order_complete", END)
builder.add_edge("order_not_found", END)
builder.add_edge("order_failed", END)

graph = builder.compile()

result = graph.invoke(
    {
        "order_id": "BAD-999",
        "attempt_count": 0,
        "status": "",
        "result": "",
    }
)

print("\n--- FINAL RESULT ---")
print(result)

# poetry run python -m lessons.lesson12_error_types