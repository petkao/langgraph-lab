
import sqlite3

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from langgraph.checkpoint.sqlite import SqliteSaver


class AgentState(TypedDict):
    request: str
    approved: bool | None
    status: str


def request_approval(state: AgentState):
    decision = interrupt({
        "question": "Do you approve this replacement?",
        "request": state["request"]
    })
    return {"approved": decision == "yes"}


def approved_node(state: AgentState):
    return {"status": "approved"}


def rejected_node(state: AgentState):
    return {"status": "rejected"}


def route_decision(state: AgentState):
    return "approved" if state["approved"] else "rejected"


builder = StateGraph(AgentState)

builder.add_node("request_approval", request_approval)
builder.add_node("approved", approved_node)
builder.add_node("rejected", rejected_node)

builder.add_edge(START, "request_approval")

builder.add_conditional_edges(
    "request_approval",
    route_decision,
    {
        "approved": "approved",
        "rejected": "rejected"
    }
)

builder.add_edge("approved", END)
builder.add_edge("rejected", END)


# Persistent SQLite connection
conn = sqlite3.connect(
    "hitl_checkpoints.db",
    check_same_thread=False
)

checkpointer = SqliteSaver(conn)
graph = builder.compile(checkpointer=checkpointer)
