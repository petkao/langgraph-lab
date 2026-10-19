
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

    await asyncio.sleep(2)

    logger.info("[%s] Processing completed", request_id)

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

        number, request_id, queued_at = item

        wait_time = time.perf_counter() - queued_at

        logger.info(
            "Worker %s picked Request %s (wait %.3fs)",
            worker_id,
            number,
            wait_time
        )

        try:
            result = await graph.ainvoke({
                "request_id": request_id,
                "result": ""
            })

            results[number] = result

        except Exception:
            logger.exception(
                "Worker %s failed Request %s",
                worker_id,
                number
            )
            results[number] = {"result": "Failed"}

        finally:
            queue.task_done()


async def main():
    queue = asyncio.Queue()
    results = {}

    start = time.perf_counter()

    workers = [
        asyncio.create_task(worker(i, queue, results))
        for i in range(1, 3)
    ]

    for number in range(1, 6):
        request_id = str(uuid.uuid4())

        await queue.put((
            number,
            request_id,
            time.perf_counter()
        ))

        logger.info("Request %s queued", number)

    await queue.join()

    for _ in workers:
        await queue.put(None)

    await asyncio.gather(*workers)

    duration = time.perf_counter() - start

    for number in sorted(results):
        print(
            f"Request {number}: "
            f"{results[number]['result']}"
        )

    print(f"Total execution time: {duration:.3f} seconds")


if __name__ == "__main__":
    asyncio.run(main())

# poetry run python queue_demo.py
