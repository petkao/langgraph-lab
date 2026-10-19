import time
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langchain_core.callbacks import BaseCallbackHandler

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)


# --------------------------------------------------
# OpenTelemetry configuration
# --------------------------------------------------

resource = Resource.create({
    "service.name": "langgraph-support-agent",
})

provider = TracerProvider(resource=resource)

provider.add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)

trace.set_tracer_provider(provider)

tracer = trace.get_tracer("langgraph-monitor")


# --------------------------------------------------
# LangGraph state
# --------------------------------------------------

class AgentState(TypedDict):
    result: str


# --------------------------------------------------
# Automatic tracing callback
# --------------------------------------------------

class OpenTelemetryCallback(BaseCallbackHandler):

    def __init__(self):
        self.spans = {}

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
        span_name = name or "unknown"

        # Find the parent span using LangGraph's run IDs
        parent_span = self.spans.get(parent_run_id)

        if parent_span:
            parent_context = trace.set_span_in_context(parent_span)
        else:
            parent_context = None

        span = tracer.start_span(
            span_name,
            context=parent_context,
        )

        span.set_attribute("langgraph.run_id", str(run_id))

        if parent_run_id:
            span.set_attribute(
                "langgraph.parent_run_id",
                str(parent_run_id),
            )

        self.spans[run_id] = span

    def on_chain_end(self, outputs, *, run_id, **kwargs):
        span = self.spans.pop(run_id, None)

        if span:
            span.end()

    def on_chain_error(self, error, *, run_id, **kwargs):
        span = self.spans.pop(run_id, None)

        if span:
            span.record_exception(error)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            span.end()


# --------------------------------------------------
# LangGraph nodes (no tracing code)
# --------------------------------------------------

def classify(state: AgentState):
    time.sleep(0.2)
    return {"result": state["result"] + " -> classify"}


def retrieve(state: AgentState):
    time.sleep(0.5)
    return {"result": state["result"] + " -> retrieve"}


def respond(state: AgentState):
    time.sleep(0.1)
    return {"result": state["result"] + " -> respond"}


# --------------------------------------------------
# Build graph
# --------------------------------------------------

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
# Execute with automatic tracing
# --------------------------------------------------

handler = OpenTelemetryCallback()

result = graph.invoke(
    {"result": "START"},
    config={"callbacks": [handler]},
)

print("\nFinal state:", result)

provider.force_flush()

# poetry run python otel_callback_demo.py
