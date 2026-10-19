import time
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langchain_core.callbacks import BaseCallbackHandler


class AgentState(TypedDict):
    result: str


class TraceHandler(BaseCallbackHandler):
    def __init__(self):
        self.start_times = {}

    def on_chain_start(
        self,
        serialized,
        inputs,
        *,
        run_id,
        parent_run_id=None,
        name=None,
        **kwargs,
    ):
        self.start_times[run_id] = time.perf_counter()

        print(
            f"[START] name={name} "
            f"run_id={run_id} "
            f"parent={parent_run_id}"
        )

    def on_chain_end(self, outputs, *, run_id, **kwargs):
        start = self.start_times.pop(run_id, None)

        if start is not None:
            elapsed = time.perf_counter() - start
            print(f"[END] run_id={run_id} duration={elapsed:.3f}s")

    def on_chain_error(self, error, *, run_id, **kwargs):
        self.start_times.pop(run_id, None)
        print(f"[ERROR] run_id={run_id} error_type={type(error).__name__}")


def classify(state: AgentState):
    time.sleep(0.2)
    return {"result": state["result"] + " -> classify"}


def retrieve(state: AgentState):
    time.sleep(0.5)
    return {"result": state["result"] + " -> retrieve"}


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

handler = TraceHandler()

result = graph.invoke(
    {"result": "START"},
    config={"callbacks": [handler]},
)

print("\nFinal state:", result)

# poetry run python automatic_tracing_demo.py
