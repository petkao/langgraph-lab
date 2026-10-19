
import hashlib
import json
import time

from typing import TypedDict
from langgraph.graph import StateGraph, START, END


cache = {}
CACHE_TTL = 10

MODEL_NAME = "demo-model-v1"
PROMPT_VERSION = "support-v1"


class AgentState(TypedDict):
    question: str
    answer: str


def generate_cache_key(question):
    normalized_question = " ".join(
        question.strip().lower().split()
    )

    payload = {
        "question": normalized_question,
        "model": MODEL_NAME,
        "prompt_version": PROMPT_VERSION
    }

    encoded = json.dumps(
        payload,
        sort_keys=True
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def call_llm(question):
    print("Calling LLM...")

    # Simulate LLM latency
    time.sleep(2)

    return (
        "To restart your laptop, save your work, "
        "open the power menu, and select Restart."
    )


def get_llm_response(question):
    key = generate_cache_key(question)
    now = time.monotonic()

    if key in cache:
        entry = cache[key]

        if now < entry["expires_at"]:
            print("LLM CACHE HIT")
            return entry["answer"]

        print("LLM CACHE EXPIRED")
        del cache[key]

    print("LLM CACHE MISS")

    answer = call_llm(question)

    cache[key] = {
        "answer": answer,
        "expires_at": time.monotonic() + CACHE_TTL
    }

    return answer


def llm_node(state: AgentState):
    answer = get_llm_response(state["question"])

    return {"answer": answer}


builder = StateGraph(AgentState)

builder.add_node("llm", llm_node)
builder.add_edge(START, "llm")
builder.add_edge("llm", END)

graph = builder.compile()


def run_request(question):
    start = time.perf_counter()

    result = graph.invoke({
        "question": question,
        "answer": ""
    })

    duration = time.perf_counter() - start

    print("Question:", question)
    print("Answer:", result["answer"])
    print(f"Execution time: {duration:.3f} seconds")
    print("-" * 40)


print("REQUEST 1")
run_request("How do I restart my laptop?")

print("REQUEST 2")
run_request("How do I restart my laptop?")

print("REQUEST 3")
run_request("How do I shut down my laptop?")

print("Waiting for cache expiration...")
time.sleep(11)

print("REQUEST 4")
run_request("How do I restart my laptop?")

# poetry run python llm_cache_demo.py
