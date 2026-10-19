
import time
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# Simple in-memory cache
cache = {}

CACHE_TTL = 5


class AgentState(TypedDict):
    product_id: str
    troubleshooting_guide: str


def fetch_troubleshooting_guide(product_id):
    print(f"Fetching guide from knowledge service: {product_id}")

    # Simulate a slow API call
    time.sleep(2)

    return f"Troubleshooting guide for {product_id}"


def get_cached_guide(product_id):
    current_time = time.monotonic()

    if product_id in cache:
        entry = cache[product_id]

        if current_time < entry["expires_at"]:
            print("CACHE HIT")
            return entry["value"]

        print("CACHE EXPIRED")
        del cache[product_id]

    print("CACHE MISS")

    guide = fetch_troubleshooting_guide(product_id)

    cache[product_id] = {
        "value": guide,
        "expires_at": time.monotonic() + CACHE_TTL
    }

    return guide


def guide_node(state: AgentState):
    guide = get_cached_guide(state["product_id"])

    return {"troubleshooting_guide": guide}


builder = StateGraph(AgentState)

builder.add_node("guide", guide_node)
builder.add_edge(START, "guide")
builder.add_edge("guide", END)

graph = builder.compile()


def run_request(product_id):
    start = time.perf_counter()

    result = graph.invoke({
        "product_id": product_id,
        "troubleshooting_guide": ""
    })

    duration = time.perf_counter() - start

    print("Result:", result["troubleshooting_guide"])
    print(f"Execution time: {duration:.3f} seconds")
    print("-" * 40)


print("REQUEST 1")
run_request("LAPTOP-100")

print("REQUEST 2")
run_request("LAPTOP-100")

print("Waiting for cache to expire...")
time.sleep(6)

print("REQUEST 3")
run_request("LAPTOP-100")

# poetry run python cache_demo.py
