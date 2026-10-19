import time
import statistics
from functools import wraps
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    result: str


# Store metrics for each node
metrics = {}


def measure_time(func):
    @wraps(func)
    def wrapper(state):
        start = time.perf_counter()

        try:
            return func(state)
        finally:
            elapsed = time.perf_counter() - start

            name = func.__name__
            metrics.setdefault(name, []).append(elapsed)

    return wrapper


@measure_time
def classify(state: AgentState):
    time.sleep(0.2)
    return {"result": state["result"] + " -> classify"}


@measure_time
def retrieve(state: AgentState):
    time.sleep(0.5)
    return {"result": state["result"] + " -> retrieve"}


@measure_time
def respond(state: AgentState):
    time.sleep(0.1)
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


# Execute the graph five times
for i in range(5):
    result = graph.invoke({"result": "START"})
    print(f"Run {i + 1}: {result['result']}")


# Calculate performance statistics
print("\nPerformance Summary")
print("-" * 55)

for name, durations in metrics.items():
    print(
        f"{name:10s} "
        f"count={len(durations)} "
        f"avg={statistics.mean(durations):.3f}s "
        f"min={min(durations):.3f}s "
        f"max={max(durations):.3f}s"
    )

    # poetry run python metrics_collection_demo.py
