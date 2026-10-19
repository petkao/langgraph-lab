
import asyncio
import logging
import time
import uuid

from collections import deque
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


class AsyncRateLimiter:
    def __init__(self, max_requests, period=1.0):
        self.max_requests = max_requests
        self.period = period
        self.timestamps = deque()
        self.lock = asyncio.Lock()

    async def acquire(self):
        while True:
            async with self.lock:
                now = time.monotonic()

                while (
                    self.timestamps
                    and now - self.timestamps[0] >= self.period
                ):
                    self.timestamps.popleft()

                if len(self.timestamps) < self.max_requests:
                    self.timestamps.append(now)
                    return

                wait_time = (
                    self.period - (now - self.timestamps[0])
                )

            await asyncio.sleep(wait_time)


async def process_request(state: AgentState):
    request_id = state["request_id"]

    logger.info("[%s] Processing started", request_id)

    await asyncio.sleep(0.2)

    logger.info("[%s] Processing completed", request_id)

    return {"result": "Success"}


builder = StateGraph(AgentState)

builder.add_node("process_request", process_request)
builder.add_edge(START, "process_request")
builder.add_edge("process_request", END)

graph = builder.compile()


async def run_request(number, limiter):
    request_id = str(uuid.uuid4())

    logger.info("Request %s waiting for rate limit", number)

    await limiter.acquire()

    logger.info("Request %s admitted", number)

    result = await graph.ainvoke({
        "request_id": request_id,
        "result": ""
    })

    return number, request_id, result


async def main():
    limiter = AsyncRateLimiter(
        max_requests=3,
        period=1.0
    )

    start = time.perf_counter()

    results = await asyncio.gather(
        *[
            run_request(i, limiter)
            for i in range(1, 11)
        ]
    )

    for number, request_id, result in results:
        print(
            f"Request {number}: "
            f"{request_id} → {result['result']}"
        )

    duration = time.perf_counter() - start

    print(f"Total execution time: {duration:.3f} seconds")


if __name__ == "__main__":
    asyncio.run(main())

# poetry run python rate_limit_demo.py
