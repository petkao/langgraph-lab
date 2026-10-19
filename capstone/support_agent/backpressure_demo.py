
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
    logger.info(
        "[%s] Processing started",
        state["request_id"]
    )

    await asyncio.sleep(2)

    logger.info(
        "[%s] Processing completed",
        state["request_id"]
    )

    return {"result": "Success"}


builder = StateGraph(AgentState)

builder.add_node("process_request", process_request)
builder.add_edge(START, "process_request")
builder.add_edge("process_request", END)

graph = builder.compile()


async def worker(worker_id, queue, results):
    while True:
        item = await queue.get()

        if item is None:
            queue.task_done()
            logger.info("Worker %s shutting down", worker_id)
            break

        number, request_id = item

        try:
            result = await graph.ainvoke({
                "request_id": request_id,
                "result": ""
            })

            results[number] = result["result"]

        except Exception:
            logger.exception(
                "Worker %s failed Request %s",
                worker_id,
                number
            )
            results[number] = "Failed"

        finally:
            queue.task_done()


async def main():
    queue = asyncio.Queue(maxsize=3)
    results = {}

    workers = [
        asyncio.create_task(worker(i, queue, results))
        for i in range(1, 3)
    ]

    start = time.perf_counter()

    for number in range(1, 11):
        request_id = str(uuid.uuid4())

        try:
            await asyncio.wait_for(
                queue.put((number, request_id)),
                timeout=0.5
            )

            logger.info("Request %s accepted", number)

        except asyncio.TimeoutError:
            logger.warning(
                "Request %s rejected: queue full",
                number
            )

            results[number] = "Rejected"

    await queue.join()

    for _ in workers:
        await queue.put(None)

    await asyncio.gather(*workers)

    duration = time.perf_counter() - start

    for number in sorted(results):
        print(f"Request {number}: {results[number]}")

    print(f"Total execution time: {duration:.3f} seconds")


if __name__ == "__main__":
    asyncio.run(main())

# poetry run python backpressure_demo.py
