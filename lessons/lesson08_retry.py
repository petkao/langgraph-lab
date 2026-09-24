from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class OrderState(TypedDict):
    order_id: str
    attempt_count: int
    status: str
'''
def retrieve_order(state: OrderState):
    attempt = state["attempt_count"] + 1

    print(f"Attempt {attempt}: retrieving {state['order_id']}")

    if attempt < 3:
        return {
            "attempt_count": attempt,
            "status": "failed"
        }

    return {
        "attempt_count": attempt,
        "status": "success"
    }
'''

def get_order(order_id: str):
    print(f"Calling order service for {order_id}")
    raise TimeoutError("Order service timed out")


def retrieve_order(state: OrderState):
    attempt = state["attempt_count"] + 1

    try:
        get_order(state["order_id"])

        return {
            "attempt_count": attempt,
            "status": "success"
        }

    except TimeoutError as error:
        print(f"Attempt {attempt} failed: {error}")

        return {
            "attempt_count": attempt,
            "status": "failed"
        }

def route_after_retrieval(state: OrderState) -> str:
    if state["status"] == "success":
        return "done"

    if state["status"] == "failed":
        if state["attempt_count"] >= 3:
            return "human"

        return "retry"

def human_review(state: OrderState):
    return {
        "status": "sent_to_human_review"
    }

builder = StateGraph(OrderState)

builder.add_node("retrieve_order", retrieve_order)
builder.add_node("human_review", human_review)

builder.add_edge(START, "retrieve_order")

builder.add_conditional_edges(
    "retrieve_order",
    route_after_retrieval,
    {
        "retry": "retrieve_order",
        "human": "human_review",
        "done": END,
    }
)

builder.add_edge("human_review", END)

graph = builder.compile()

result = graph.invoke({
    "order_id": "ORD-123",
    "attempt_count": 0,
    "status": ""
})

print(result)

# poetry run python lessons/lesson08_retry.py