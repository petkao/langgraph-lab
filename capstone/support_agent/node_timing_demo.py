import time
from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    result: str


def timed_node(name, duration):
    def node(state: AgentState):
        start = time.perf_counter()

        time.sleep(duration)

        elapsed = time.perf_counter() - start
        print(f"{name}: {elapsed:.3f} seconds")

        return {"result": state["result"] + f" -> {name}"}

    return node


builder = StateGraph(AgentState)

builder.add_node("classify", timed_node("classify", 0.5))
builder.add_node("retrieve", timed_node("retrieve", 1.0))
builder.add_node("respond", timed_node("respond", 0.3))

builder.add_edge(START, "classify")
builder.add_edge("classify", "retrieve")
builder.add_edge("retrieve", "respond")
builder.add_edge("respond", END)

graph = builder.compile()

start = time.perf_counter()

result = graph.invoke({"result": "START"})

total = time.perf_counter() - start

print("\nFinal state:", result)
print(f"Total workflow time: {total:.3f} seconds")

# poetry run python node_timing_demo.py
