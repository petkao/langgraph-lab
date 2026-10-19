from dotenv import load_dotenv
from fastapi import requests
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from langgraph.types import Command
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

logger = logging.getLogger("langgraph_api")

load_dotenv()

DB_URI = os.environ["LANGGRAPH_DATABASE_URL"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create a connection pool when FastAPI starts.
    with ConnectionPool(
        conninfo=DB_URI,
        min_size=1,
        max_size=5,
        kwargs={"autocommit": True, "prepare_threshold": None},
    ) as pool:

        checkpointer = PostgresSaver(pool)
        checkpointer.setup()

        from hitl_graph_postgres import builder

        app.state.graph = builder.compile(
            checkpointer=checkpointer
        )

        print("PostgreSQL LangGraph initialized")

        yield

        print("PostgreSQL connection pool shutting down")


app = FastAPI(
    title="LangGraph HITL PostgreSQL API",
    lifespan=lifespan
)

graph_semaphore = threading.BoundedSemaphore(2)

# Protect access to the lock dictionary.
thread_locks_guard = threading.Lock()

# One lock per LangGraph thread.
thread_locks = {}


def get_thread_lock(thread_id: str):
    with thread_locks_guard:
        if thread_id not in thread_locks:
            thread_locks[thread_id] = threading.Lock()

        return thread_locks[thread_id]

class ReplacementRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    request: str = Field(min_length=1)


class ApprovalRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    decision: str = Field(pattern=r"(?i)^\s*(yes|no)\s*$")


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/replacement")
def start_replacement(
    request: ReplacementRequest,
    http_request: Request
):
    graph = http_request.app.state.graph

    config = {
        "configurable": {
            "thread_id": request.thread_id
        }
    }

    # Serialize requests for the same LangGraph thread.
    thread_lock = get_thread_lock(request.thread_id)

    with thread_lock:
        # Check and execute while holding the same lock.
        snapshot = graph.get_state(config)

        if snapshot.values or snapshot.next:
            raise HTTPException(
                status_code=409,
                detail="Thread already exists"
            )

        # Limit total concurrent graph executions.
        with graph_semaphore:
            try:
                logger.info(
                    "Starting replacement workflow: thread_id=%s",
                    request.thread_id
                )

                result = graph.invoke(
                    {
                        "request": request.request,
                        "approved": None,
                        "status": "pending"
                    },
                    config=config
                )

            except Exception:
                logger.exception(
                    "Replacement workflow failed: thread_id=%s",
                    request.thread_id
                )

                raise HTTPException(
                    status_code=500,
                    detail="Replacement workflow failed"
                )

    return {
        "thread_id": request.thread_id,
        "result": result
    }


@app.post("/approval")
def submit_approval(
    request: ApprovalRequest,
    http_request: Request
):
    graph = http_request.app.state.graph

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

    # Serialize approval requests for the same thread.
    thread_lock = get_thread_lock(request.thread_id)

    with thread_lock:
        snapshot = graph.get_state(config)

        if "request_approval" not in snapshot.next:
            raise HTTPException(
                status_code=409,
                detail="No pending approval for this thread"
            )

        with graph_semaphore:
            result = graph.invoke(
                Command(resume=decision),
                config=config
            )

    return {
        "thread_id": request.thread_id,
        "result": result
    }



@app.get("/state/{thread_id}")
def get_thread_state(
    thread_id: str,
    http_request: Request
):
    graph = http_request.app.state.graph
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
