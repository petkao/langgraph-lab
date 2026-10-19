
import asyncio
import time
import uuid

import httpx

BASE_URL = "http://127.0.0.1:8000"


async def send_request(client, number, run_id):
    thread_id = f"concurrent-{run_id}-{number}"

    payload = {
        "thread_id": thread_id,
        "request": f"Replace defective laptop {number}"
    }

    start = time.perf_counter()

    try:
        response = await client.post(
            f"{BASE_URL}/replacement",
            json=payload
        )

        elapsed = time.perf_counter() - start

        print(
            f"Request {number}: "
            f"HTTP {response.status_code}, "
            f"{elapsed:.3f} seconds"
        )

        if response.status_code == 200:
            result = response.json()["result"]
            print(
                f"  thread_id: {thread_id}, "
                f"status: {result.get('status')}, "
                f"interrupted: {'__interrupt__' in result}"
            )
        else:
            print(f"  Error: {response.text}")

    except Exception as exc:
        print(
            f"Request {number} failed: "
            f"{type(exc).__name__}: {exc!r}"
        )


async def main():
    run_id = uuid.uuid4().hex[:8]

    async with httpx.AsyncClient(
        timeout=30.0
    ) as client:

        start = time.perf_counter()

        await asyncio.gather(
            *[
                send_request(client, i, run_id)
                for i in range(1, 6)
            ]
        )

        elapsed = time.perf_counter() - start

        print(f"\nTotal elapsed: {elapsed:.3f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
