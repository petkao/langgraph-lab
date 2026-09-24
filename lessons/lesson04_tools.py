# print("LESSON 04 FILE STARTED")

from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class OrderState(TypedDict):
    order_id: str
    amount: float
    order_status: str

def get_order(order_id: str):
    print(f"Looking up order: {order_id}")

    return {
        "order_id": order_id,
        "amount": 300.00,
        "status": "delivered"
    }

def retrieve_order(state: OrderState):

    order = get_order(state["order_id"])

    return {
        "amount": order["amount"],
        "order_status": order["status"]
    }

builder = StateGraph(OrderState)

builder.add_node(
    "retrieve_order",
    retrieve_order
)

builder.add_edge(START, "retrieve_order")
builder.add_edge("retrieve_order", END)

graph = builder.compile()

# print("ABOUT TO INVOKE GRAPH")

result = graph.invoke({
    "order_id": "ORD-123",
    "amount": 0.0,
    "order_status": ""
})

# print("GRAPH FINISHED")

print(result)

# poetry run python lessons/lesson04_tools.py


