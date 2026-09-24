from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool


class RefundState(TypedDict):
    refund_id: str
    approval_id: str
    amount: float
    approval_status: str
    result: str

def request_approval(state: RefundState):

    decision = interrupt(
        {
            "approval_id": state["approval_id"],
            "refund_id": state["refund_id"],
            "amount": state["amount"],
            "message": "Human approval required",
        }
    )

    return {
        "approval_status": decision
    }  

def route_decision(state: RefundState):
    if state["approval_status"] == "approved":
        return "approved"
    else:
        return "rejected"

def process_refund(state: RefundState):
    return {
        "result": f"Refund {state['refund_id']} approved for ${state['amount']}"
    }


def reject_refund(state: RefundState):
    return {
        "result": f"Refund {state['refund_id']} was rejected"
    }

builder = StateGraph(RefundState)

builder.add_node("request_approval", request_approval)
builder.add_node("process_refund", process_refund)
builder.add_node("reject_refund", reject_refund)

builder.add_edge(START, "request_approval")

builder.add_conditional_edges(
    "request_approval",
    route_decision,
    {
        "approved": "process_refund",
        "rejected": "reject_refund",
    },
)

builder.add_edge("process_refund", END)
builder.add_edge("reject_refund", END)

DB_URI = "postgresql://tzechungkao@localhost:5432/langgraph_lab"

pool = ConnectionPool(
    conninfo=DB_URI,
    max_size=10,
    open=False,
    kwargs={
        "autocommit": True,
        "prepare_threshold": 0,
    },
)

checkpointer = PostgresSaver(pool)

graph = builder.compile(
    checkpointer=checkpointer
)

if __name__ == "__main__":

    config = {
        "configurable": {
            "thread_id": "lesson13-refund-001"
        }
    }

    result = graph.invoke(
        {
            "refund_id": "REF-5001",
            "approval_id": "APR-7001",
            "amount": 1200.00,
            "approval_status": "",
            "result": "",
        },
        config=config,
    )

    print("\nFIRST INVOCATION:")
    print(result)

    pool.close()