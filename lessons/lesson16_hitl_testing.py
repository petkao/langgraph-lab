from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command

class ApprovalState(TypedDict):
    amount: float
    approval_status: str
    result: str

def request_approval(state: ApprovalState):

    decision = interrupt(
        {
            "amount": state["amount"],
            "message": "Approval required",
        }
    )

    return {
        "approval_status": decision
    }

def route_decision(state: ApprovalState):

    if state["approval_status"] == "approved":
        return "approved"

    if state["approval_status"] == "rejected":
        return "rejected"

    return "invalid"

def process_approval(state: ApprovalState):

    return {
        "result": "Refund approved"
    }


def process_rejection(state: ApprovalState):

    return {
        "result": "Refund rejected"
    }


def process_invalid(state: ApprovalState):

    return {
        "result": "Invalid decision"
    }

checkpointer = InMemorySaver()

builder = StateGraph(ApprovalState)

builder.add_node(
    "request_approval",
    request_approval
)

builder.add_node(
    "process_approval",
    process_approval
)

builder.add_node(
    "process_rejection",
    process_rejection
)

builder.add_node(
    "process_invalid",
    process_invalid
)

builder.add_edge(
    START,
    "request_approval"
)

builder.add_conditional_edges(
    "request_approval",
    route_decision,
    {
        "approved": "process_approval",
        "rejected": "process_rejection",
        "invalid": "process_invalid",
    }
)

builder.add_edge("process_approval", END)
builder.add_edge("process_rejection", END)
builder.add_edge("process_invalid", END)

graph = builder.compile(
    checkpointer=checkpointer
)

def test_approval_pause_and_resume():

    config = {
        "configurable": {
            "thread_id": "test-approval-001"
        }
    }

    first_result = graph.invoke(
        {
            "amount": 1200,
            "approval_status": "",
            "result": "",
        },
        config=config,
    )

    assert "__interrupt__" in first_result

    resumed_result = graph.invoke(
        Command(resume="approved"),
        config=config,
    )

    assert resumed_result["approval_status"] == "approved"
    assert resumed_result["result"] == "Refund approved"

test_approval_pause_and_resume()

print("HITL test passed.")