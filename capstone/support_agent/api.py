
import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.types import Command

from hitl_graph_sqlite import graph

app = FastAPI(title="LangGraph HITL API")
graph_semaphore = threading.BoundedSemaphore(2)

class ReplacementRequest(BaseModel):
    thread_id: str
    request: str


class ApprovalRequest(BaseModel):
    thread_id: str
    decision: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/replacement")
def start_replacement(request: ReplacementRequest):
    config = {
        "configurable": {
            "thread_id": request.thread_id
        }
    }

    # Do not overwrite an existing thread.
    snapshot = graph.get_state(config)
    if snapshot.values or snapshot.next:
        raise HTTPException(
            status_code=409,
            detail="Thread already exists"
        )

    with graph_semaphore:
        result = graph.invoke(
            {
                "request": request.request,
                "approved": None,
                "status": "pending"
            },
            config=config
        )

    return {
        "thread_id": request.thread_id,
        "result": result
    }


@app.post("/approval")
def submit_approval(request: ApprovalRequest):
    config = {
        "configurable": {
            "thread_id": request.thread_id
        }
    }

    decision = request.decision.lower().strip()

    if decision not in ("yes", "no"):
        raise HTTPException(
            status_code=400,
            detail="Decision must be yes or no"
        )

    snapshot = graph.get_state(config)

    if "request_approval" not in snapshot.next:
        raise HTTPException(
            status_code=409,
            detail="No pending approval for this thread"
        )

    result = graph.invoke(
        Command(resume=decision),
        config=config
    )

    return {
        "thread_id": request.thread_id,
        "result": result
    }


@app.get("/state/{thread_id}")
def get_thread_state(thread_id: str):
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    snapshot = graph.get_state(config)

    if not snapshot.values and not snapshot.next:
        raise HTTPException(
            status_code=404,
            detail="Thread not found"
        )

    return {
        "thread_id": thread_id,
        "state": snapshot.values,
        "next": list(snapshot.next),
        "created_at": snapshot.created_at
    }
