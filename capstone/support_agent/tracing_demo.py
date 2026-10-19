
import logging
import time
import uuid

from typing import TypedDict
from langgraph.graph import StateGraph, START, END

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    request_id: str
    result: str


def validate_request(state: AgentState):
    request_id = state["request_id"]
    start = time.perf_counter()

    logger.info("[%s] validate_request started", request_id)

    time.sleep(0.5)

    duration = time.perf_counter() - start

    logger.info(
        "[%s] validate_request completed in %.3f seconds",
        request_id,
        duration
    )

    return {}


def process_request(state: AgentState):
    request_id = state["request_id"]
    start = time.perf_counter()

    logger.info("[%s] process_request started", request_id)

    time.sleep(1)

    duration = time.perf_counter() - start

    logger.info(
        "[%s] process_request completed in %.3f seconds",
        request_id,
        duration
    )

    return {"result": "Request processed successfully"}


builder = StateGraph(AgentState)

builder.add_node("validate_request", validate_request)
builder.add_node("process_request", process_request)

builder.add_edge(START, "validate_request")
builder.add_edge("validate_request", "process_request")
builder.add_edge("process_request", END)

graph = builder.compile()

request_id = str(uuid.uuid4())

result = graph.invoke({
    "request_id": request_id,
    "result": ""
})

print("Final result:", result)

# poetry run python tracing_demo.py
