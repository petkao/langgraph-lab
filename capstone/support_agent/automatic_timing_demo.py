import time
from functools import wraps
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    result: str


# Reusable timing decorator
def measure_time(func):
    @wraps(func)
    def wrapper(state):
        start = time.perf_counter()

        try:
            return func(state)
        finally:
            elapsed = time.perf_counter() - start
            print(f"[METRIC] {func.__name__}: {elapsed:.3f}s")

    return wrapper


@measure_time
def classify(state: AgentState):
    time.sleep(0.5)
    return {"result": state["result"] + " -> classify"}


@measure_time
def retrieve(state: AgentState):
    time.sleep(1.0)
    return {"result": state["result"] + " -> retrieve"}


@measure_time
def respond(state: AgentState):
    time.sleep(0.3)
    return {"result": state["result"] + " -> respond"}


builder = StateGraph(AgentState)

builder.add_node("classify", classify)
builder.add_node("retrieve", retrieve)
builder.add_node("respond", respond)

builder.add_edge(START, "classify")
builder.add_edge("classify", "retrieve")
builder.add_edge("retrieve", "respond")
builder.add_edge("respond", END)

graph = builder.compile()

result = graph.invoke({"result": "START"})

print("\nFinal state:", result)

# poetry run python automatic_timing_demo.py
