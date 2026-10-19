
import asyncio
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


async def process_request(state: AgentState):
    request_id = state["request_id"]

    logger.info("[%s] Processing started", request_id)

    # Simulate a nonblocking I/O operation
    await asyncio.sleep(2)

    logger.info("[%s] Processing completed", request_id)

    return {"result": "Success"}


builder = StateGraph(AgentState)

builder.add_node("process_request", process_request)
builder.add_edge(START, "process_request")
builder.add_edge("process_request", END)

graph = builder.compile()


async def run_request(request_number):
    request_id = str(uuid.uuid4())

    result = await graph.ainvoke({
        "request_id": request_id,
        "result": ""
    })

    return request_number, request_id, result


async def main():
    start = time.perf_counter()

    results = await asyncio.gather(
        run_request(1),
        run_request(2),
        run_request(3)
    )

    duration = time.perf_counter() - start

    for number, request_id, result in results:
        print(
            f"Request {number}: "
            f"{request_id} → {result['result']}"
        )

    print(f"Total execution time: {duration:.3f} seconds")


if __name__ == "__main__":
    asyncio.run(main())

# poetry run python async_tracing_demo.py
