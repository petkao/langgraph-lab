
import logging
import time
import uuid

from concurrent.futures import ThreadPoolExecutor
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


def process_request(state: AgentState):
    request_id = state["request_id"]

    logger.info("[%s] Processing started", request_id)

    time.sleep(2)

    logger.info("[%s] Processing completed", request_id)

    return {"result": "Success"}


builder = StateGraph(AgentState)

builder.add_node("process_request", process_request)
builder.add_edge(START, "process_request")
builder.add_edge("process_request", END)

graph = builder.compile()


def run_request(request_number):
    request_id = str(uuid.uuid4())

    result = graph.invoke({
        "request_id": request_id,
        "result": ""
    })

    return request_number, request_id, result


start = time.perf_counter()

with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(run_request, range(1, 4)))

duration = time.perf_counter() - start

for number, request_id, result in results:
    print(
        f"Request {number}: "
        f"{request_id} → {result['result']}"
    )

print(f"Total execution time: {duration:.3f} seconds")

# poetry run python concurrent_tracing_demo.py
