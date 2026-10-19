
import logging
import time

from typing import TypedDict
from langgraph.graph import StateGraph, START, END

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    result: str


def process_request(state: AgentState):
    logger.info("Starting process_request node")

    start_time = time.perf_counter()

    time.sleep(1)

    result = "Request processed successfully"

    duration = time.perf_counter() - start_time

    logger.info(
        "process_request completed in %.3f seconds",
        duration
    )

    return {"result": result}


builder = StateGraph(AgentState)

builder.add_node("process_request", process_request)

builder.add_edge(START, "process_request")
builder.add_edge("process_request", END)

graph = builder.compile()

result = graph.invoke({"result": ""})

print("Final result:", result)

# poetry run python logging_demo.py
