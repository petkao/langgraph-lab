import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# Configure Python logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logger = logging.getLogger("support_agent")


class AgentState(TypedDict):
    thread_id: str
    result: str


def log_event(thread_id, node, event, status):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "thread_id": thread_id,
        "node": node,
        "event": event,
        "status": status,
    }

    logger.info(json.dumps(record))


def classify(state: AgentState):
    log_event(state["thread_id"], "classify", "started", "running")

    time.sleep(0.2)

    log_event(state["thread_id"], "classify", "completed", "success")

    return {"result": state["result"] + " -> classify"}


def retrieve(state: AgentState):
    log_event(state["thread_id"], "retrieve", "started", "running")

    time.sleep(0.5)

    log_event(state["thread_id"], "retrieve", "completed", "success")

    return {"result": state["result"] + " -> retrieve"}


def respond(state: AgentState):
    log_event(state["thread_id"], "respond", "started", "running")

    time.sleep(0.1)

    log_event(state["thread_id"], "respond", "completed", "success")

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


# Simulate two independent customer requests
for i in range(2):
    thread_id = f"customer-{uuid.uuid4().hex[:8]}"

    result = graph.invoke({
        "thread_id": thread_id,
        "result": "START",
    })

    print(f"\nRequest {i + 1}: {result['thread_id']}")
    print("Final result:", result["result"])

    # poetry run python structured_logging_demo.py
