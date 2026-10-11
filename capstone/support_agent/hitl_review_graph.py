
import sqlite3
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from langgraph.checkpoint.sqlite import SqliteSaver


class AgentState(TypedDict):
    order_id: str
    proposed_quantity: int
    approved_quantity: int | None
    status: str


def human_review(state: AgentState):
    response = interrupt({
        "question": "Review the replacement proposal",
        "order_id": state["order_id"],
        "proposed_quantity": state["proposed_quantity"]
    })

    action = response["action"]

    if action == "reject":
        return {
            "approved_quantity": None,
            "status": "rejected"
        }

    if action not in ("approve", "modify"):
        raise ValueError("Invalid review action")

    if action == "approve":
        quantity = state["proposed_quantity"]
    else:
        quantity = response["quantity"]

    if type(quantity) is not int or quantity < 1:
        raise ValueError("Quantity must be a positive integer")

    return {
        "approved_quantity": quantity,
        "status": "approved"
    }


builder = StateGraph(AgentState)

builder.add_node("human_review", human_review)

builder.add_edge(START, "human_review")
builder.add_edge("human_review", END)


db_path = Path(__file__).with_name("hitl_review.db")

conn = sqlite3.connect(
    str(db_path),
    check_same_thread=False
)

checkpointer = SqliteSaver(conn)
graph = builder.compile(checkpointer=checkpointer)
