import time
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langchain_core.callbacks import BaseCallbackHandler

from prometheus_client import Counter, Histogram, generate_latest


# --------------------------------------------------
# Prometheus metrics
# --------------------------------------------------

NODE_EXECUTIONS = Counter(
    "langgraph_node_executions_total",
    "Total number of LangGraph node executions",
    ["node", "status"],
)

NODE_DURATION = Histogram(
    "langgraph_node_duration_seconds",
    "LangGraph node execution duration in seconds",
    ["node"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# --------------------------------------------------
# Automatic instrumentation using callbacks
# --------------------------------------------------

class PrometheusCallback(BaseCallbackHandler):

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
        if parent_run_id is None:
            return  # Skip the overall graph

        self.start_times[run_id] = (
            name or "unknown",
            time.perf_counter(),
        )

    def on_chain_end(self, outputs, *, run_id, **kwargs):
        entry = self.start_times.pop(run_id, None)

        if entry is None:
            return

        name, start = entry
        elapsed = time.perf_counter() - start

        NODE_EXECUTIONS.labels(
            node=name,
            status="success",
        ).inc()

        NODE_DURATION.labels(node=name).observe(elapsed)

    def on_chain_error(self, error, *, run_id, **kwargs):
        entry = self.start_times.pop(run_id, None)

        if entry is None:
            return

        name, start = entry
        elapsed = time.perf_counter() - start

        NODE_EXECUTIONS.labels(
            node=name,
            status="error",
        ).inc()

        NODE_DURATION.labels(node=name).observe(elapsed)


# --------------------------------------------------
# LangGraph nodes
# --------------------------------------------------

class AgentState(TypedDict):
    result: str


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


# --------------------------------------------------
# Execute five workflows
# --------------------------------------------------

handler = PrometheusCallback()

for i in range(5):
    graph.invoke(
        {"result": "START"},
        config={"callbacks": [handler]},
    )
    print(f"Completed workflow {i + 1}")


# --------------------------------------------------
# Display Prometheus metrics
# --------------------------------------------------

metrics_text = generate_latest().decode("utf-8")

for line in metrics_text.splitlines():
    if line.startswith("langgraph_node_"):
        print(line)


# poetry run python prometheus_metrics_demo.py
