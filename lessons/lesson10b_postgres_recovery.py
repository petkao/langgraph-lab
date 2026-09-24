from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver


class State(TypedDict):
    count: int


def increment(state: State):
    return {
        "count": state["count"] + 1
    }


builder = StateGraph(State)

builder.add_node("increment", increment)

builder.add_edge(START, "increment")
builder.add_edge("increment", END)


DB_URI = "postgresql://tzechungkao@localhost:5432/langgraph_lab"


with PostgresSaver.from_conn_string(DB_URI) as checkpointer:

    graph = builder.compile(
        checkpointer=checkpointer
    )

    config = {
        "configurable": {
            "thread_id": "postgres-test-001"
        }
    }

    snapshot = graph.get_state(config)

    print("Recovered state:", snapshot.values)