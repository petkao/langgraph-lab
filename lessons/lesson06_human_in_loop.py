from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command


class RefundState(TypedDict):
    customer_name: str
    refund_amount: float
    human_decision: str
    status: str


def review_refund(state: RefundState):
    amount = state["refund_amount"]

    if amount <= 500:
        return {
            "status": "Refund approved automatically."
        }

    decision = interrupt({
        "question": "Approve this refund?",
        "customer_name": state["customer_name"],
        "refund_amount": amount,
    })

    return {
        "human_decision": decision
    }


def finalize_refund(state: RefundState):
    if state["human_decision"] == "approve":
        return {
            "status": "Refund approved by human reviewer."
        }

    return {
        "status": "Refund rejected by human reviewer."
    }


builder = StateGraph(RefundState)

builder.add_node("review_refund", review_refund)
builder.add_node("finalize_refund", finalize_refund)

builder.add_edge(START, "review_refund")
builder.add_edge("review_refund", "finalize_refund")
builder.add_edge("finalize_refund", END)

checkpointer = InMemorySaver()

graph = builder.compile(
    checkpointer=checkpointer
)


config = {
    "configurable": {
        "thread_id": "refund-001"
    }
}


result = graph.invoke(
    {
        "customer_name": "Peter",
        "refund_amount": 700.00,
        "human_decision": "",
        "status": "",
    },
    config=config
)

print("\n--- AFTER FIRST INVOCATION ---")
print(result)

human_response = input(
    "\nEnter decision (approve/reject): "
)

print("\nHuman selected:", human_response)

result2 = graph.invoke(
    Command(resume=human_response),
    config=config
)

print("\n--- AFTER RESUME ---")
print(result2)

# poetry run python lessons/lesson06_human_in_loop.py