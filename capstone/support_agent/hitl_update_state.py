
import sqlite3
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver


class AgentState(TypedDict):
    order_id: str
    proposed_quantity: int
    status: str


def review_proposal(state: AgentState):
    print("Reviewing proposal:", state)
    return {"status": "reviewed"}


builder = StateGraph(AgentState)

builder.add_node("review_proposal", review_proposal)

builder.add_edge(START, "review_proposal")
builder.add_edge("review_proposal", END)


db_path = Path(__file__).with_name("hitl_update_state.db")

conn = sqlite3.connect(
    str(db_path),
    check_same_thread=False
)

checkpointer = SqliteSaver(conn)

graph = builder.compile(checkpointer=checkpointer)


config = {
    "configurable": {
        "thread_id": "update-state-001"
    }
}


# Create an initial checkpoint without executing the graph
graph.update_state(
    config,
    {
        "order_id": "ORD-1001",
        "proposed_quantity": 2,
        "status": "pending"
    },
    as_node="__start__"
)

snapshot = graph.get_state(config)

print("\nInitial checkpoint:")
print(snapshot.values)
print("Next:", snapshot.next)

# Modify the existing checkpoint
graph.update_state(
    config,
    {
        "proposed_quantity": 1
    },
    as_node="__start__"
)

# Retrieve the updated checkpoint
snapshot = graph.get_state(config)

print("\nUpdated checkpoint:")
print(snapshot.values)
print("Next:", snapshot.next)

# Execute the pending node using the updated checkpoint
result = graph.invoke(None, config=config)

print("\nFinal result:")
print(result)

snapshot = graph.get_state(config)

print("Next:", snapshot.next)

# poetry run python hitl_update_state.py
