
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy

import requests

class State(TypedDict):
    result: str


attempts = 0


def unreliable_node(state: State):
    global attempts
    attempts += 1

    print(f"Attempt {attempts}")

    if attempts < 3:
        raise requests.exceptions.Timeout("Simulated API timeout")

    return {"result": "Success after retry"}


builder = StateGraph(State)

builder.add_node(
    "unreliable_node",
    unreliable_node,
    retry_policy=RetryPolicy(
        max_attempts=3,
        initial_interval=0.5,
        backoff_factor=2.0,
        max_interval=2.0,
        jitter=False,
        retry_on=(ConnectionError, requests.exceptions.Timeout),
    ),
)

builder.add_edge(START, "unreliable_node")
builder.add_edge("unreliable_node", END)

graph = builder.compile()

result = graph.invoke({"result": ""})

print("Final result:", result)
