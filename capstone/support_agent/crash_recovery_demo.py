
import sqlite3
import sys
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver


BASE_DIR = Path(__file__).resolve().parent
CHECKPOINT_DB = BASE_DIR / "recovery_checkpoints.db"
BUSINESS_DB = BASE_DIR / "replacement_records.db"

THREAD_ID = "replacement-recovery-001"
ORDER_ID = "ORD-1001"
REQUEST_ID = "REQ-1001"
IDEMPOTENCY_KEY = f"replacement-{REQUEST_ID}"


class AgentState(TypedDict):
    order_id: str
    request_id: str
    replacement_id: str
    status: str


def initialize_business_db():
    with sqlite3.connect(BUSINESS_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS replacements (
                idempotency_key TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                replacement_id TEXT NOT NULL
            )
        """)


def submit_replacement(order_id, idempotency_key):
    with sqlite3.connect(BUSINESS_DB) as conn:
        existing = conn.execute(
            """
            SELECT replacement_id
            FROM replacements
            WHERE idempotency_key = ?
            """,
            (idempotency_key,)
        ).fetchone()

        if existing:
            print("Existing replacement found:", existing[0])
            return existing[0]

        replacement_id = "RPL-" + order_id

        conn.execute(
            """
            INSERT INTO replacements
            (idempotency_key, order_id, replacement_id)
            VALUES (?, ?, ?)
            """,
            (idempotency_key, order_id, replacement_id)
        )

        print("New replacement created:", replacement_id)
        return replacement_id


def replacement_node(state: AgentState):
    replacement_id = submit_replacement(
        state["order_id"],
        IDEMPOTENCY_KEY
    )

    if "--crash" in sys.argv:
        print("Simulating crash before checkpoint...")
        sys.stdout.flush()
        sys.stderr.flush()
        import os
        os._exit(1)

    return {
        "replacement_id": replacement_id,
        "status": "completed"
    }


def build_graph(checkpointer):
    builder = StateGraph(AgentState)

    builder.add_node("replacement", replacement_node)
    builder.add_edge(START, "replacement")
    builder.add_edge("replacement", END)

    return builder.compile(checkpointer=checkpointer)


def main():
    initialize_business_db()

    config = {
        "configurable": {
            "thread_id": THREAD_ID
        }
    }

    with SqliteSaver.from_conn_string(
        str(CHECKPOINT_DB)
    ) as checkpointer:

        graph = build_graph(checkpointer)

        snapshot = graph.get_state(config)

        if snapshot.values:
            print("Previous state:", snapshot.values)

        if snapshot.next:
            print("Resuming pending workflow...")
            graph_input = None
        elif snapshot.values.get("status") == "completed":
            print("Workflow already completed.")
            return
        else:
            print("Starting replacement workflow...")
            graph_input = {
                "order_id": ORDER_ID,
                "request_id": REQUEST_ID,
                "replacement_id": "",
                "status": "pending"
            }

        result = graph.invoke(
            graph_input,
            config=config
        )

        print("Final state:", result)


if __name__ == "__main__":
    main()

# poetry run python crash_recovery_demo.py --crash
