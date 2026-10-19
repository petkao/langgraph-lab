
import os

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from langgraph.checkpoint.postgres import PostgresSaver


class AgentState(TypedDict):
    request: str
    approved: bool | None
    status: str


import time

def request_approval(state: AgentState):

    print(f"START processing: {state['request']}")

    time.sleep(2)

    print(f"FINISH processing: {state['request']}")

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

'''
# PostgreSQL checkpoint connection
DB_URI = os.environ["LANGGRAPH_DATABASE_URL"]

postgres_context = PostgresSaver.from_conn_string(DB_URI)
checkpointer = postgres_context.__enter__()

# Initialize PostgreSQL checkpoint tables
checkpointer.setup()

graph = builder.compile(checkpointer=checkpointer)
'''

# Compile the graph without initializing PostgreSQL.
# FastAPI will attach its managed checkpointer.

graph = builder.compile()
