
import time
from typing import TypedDict

from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage


cache = {}
CACHE_TTL = 5


def fetch_order_from_database(order_id):
    print(f"Querying order database: {order_id}")
    time.sleep(2)

    orders = {
        "ORD-1001": {
            "product": "Laptop",
            "status": "delivered"
        },
        "ORD-1002": {
            "product": "Monitor",
            "status": "shipped"
        }
    }

    return orders.get(order_id, {"status": "not_found"})


@tool
def get_order(order_id: str) -> dict:
    """Retrieve order information using an order ID."""

    now = time.monotonic()

    if order_id in cache:
        entry = cache[order_id]

        if now < entry["expires_at"]:
            print(f"CACHE HIT: {order_id}")
            return entry["value"]

        print(f"CACHE EXPIRED: {order_id}")
        del cache[order_id]

    print(f"CACHE MISS: {order_id}")

    result = fetch_order_from_database(order_id)

    cache[order_id] = {
        "value": result,
        "expires_at": time.monotonic() + CACHE_TTL
    }

    return result


class AgentState(TypedDict):
    messages: list


tool_node = ToolNode([get_order])


def call_tool(state: AgentState):
    tool_call = {
        "name": "get_order",
        "args": {"order_id": "ORD-1001"},
        "id": "call_001",
        "type": "tool_call"
    }

    return {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[tool_call]
            )
        ]
    }


builder = StateGraph(AgentState)

builder.add_node("call_tool", call_tool)
builder.add_node("tools", tool_node)

builder.add_edge(START, "call_tool")
builder.add_edge("call_tool", "tools")
builder.add_edge("tools", END)

graph = builder.compile()


def run_request():
    start = time.perf_counter()

    result = graph.invoke({"messages": []})

    duration = time.perf_counter() - start

    print("Tool result:", result["messages"][-1].content)
    print(f"Execution time: {duration:.3f} seconds")
    print("-" * 40)


print("REQUEST 1")
run_request()

print("REQUEST 2")
run_request()

print("Waiting for cache expiration...")
time.sleep(6)

print("REQUEST 3")
run_request()

# poetry run python tool_cache_demo.py
