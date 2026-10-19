import time
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)


# Configure OpenTelemetry
provider = TracerProvider()

provider.add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)

trace.set_tracer_provider(provider)

tracer = trace.get_tracer("support_agent")


class AgentState(TypedDict):
    result: str


def classify(state: AgentState):
    with tracer.start_as_current_span("classify"):
        time.sleep(0.2)
        return {"result": state["result"] + " -> classify"}


def retrieve(state: AgentState):
    with tracer.start_as_current_span("retrieve"):
        time.sleep(0.5)
        return {"result": state["result"] + " -> retrieve"}


def respond(state: AgentState):
    with tracer.start_as_current_span("respond"):
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


# Create a parent span for the entire workflow
with tracer.start_as_current_span("support_agent_workflow"):
    result = graph.invoke({"result": "START"})

print("\nFinal state:", result)

# poetry run python opentelemetry_demo.py
