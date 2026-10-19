import time
from typing import TypedDict

from fastapi import FastAPI, Response
from langgraph.graph import StateGraph, START, END
from langchain_core.callbacks import BaseCallbackHandler

from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


# --------------------------------------------------
# FastAPI
# --------------------------------------------------

app = FastAPI(title="LangGraph Prometheus Demo")


# --------------------------------------------------
# Prometheus metrics
# --------------------------------------------------

NODE_EXECUTIONS = Counter(
    "langgraph_node_executions_total",
    "Total LangGraph node executions",
    ["node", "status"],
)

NODE_DURATION = Histogram(
    "langgraph_node_duration_seconds",
    "LangGraph node execution duration",
    ["node"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# --------------------------------------------------
# Automatic instrumentation
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
            return

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
# LangGraph
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
# FastAPI endpoints
# --------------------------------------------------

@app.post("/run")
def run_workflow():
    # A separate callback for each request
    handler = PrometheusCallback()

    result = graph.invoke(
        {"result": "START"},
        config={"callbacks": [handler]},
    )

    return result


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

@app.get("/health/live")
def liveness_check():
    return {
        "status": "alive",
        "service": "langgraph-support-agent"
    }

from fastapi import Response, status

# Simulated dependency availability
dependency_ready = True


@app.get("/health/ready")
def readiness_check(response: Response):
    if not dependency_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "reason": "Required dependency unavailable"
        }

    return {
        "status": "ready",
        "service": "langgraph-support-agent"
    }



# poetry run uvicorn prometheus_fastapi_demo:app --reload
