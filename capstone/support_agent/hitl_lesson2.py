
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver


# 1. Define state
class AgentState(TypedDict):
    request: str
    approved: bool | None
    status: str


# 2. Request human approval
def request_approval(state: AgentState):
    decision = interrupt({
        "question": "Do you approve this replacement?",
        "request": state["request"]
    })

    return {"approved": decision == "yes"}


# 3. Approved node
def approved_node(state: AgentState):
    print("Replacement APPROVED")
    return {"status": "approved"}


# 4. Rejected node
def rejected_node(state: AgentState):
    print("Replacement REJECTED")
    return {"status": "rejected"}


# 5. Conditional routing
def route_decision(state: AgentState):
    if state["approved"]:
        return "approved"
    return "rejected"


# 6. Build graph
builder = StateGraph(AgentState)

builder.add_node("request_approval", request_approval)
builder.add_node("approved", approved_node)
builder.add_node("rejected", rejected_node)

builder.add_edge(START, "request_approval")

builder.add_conditional_edges(
    "request_approval",
    route_decision,
    {
        "approved": "approved",
        "rejected": "rejected"
    }
)

builder.add_edge("approved", END)
builder.add_edge("rejected", END)


# 7. Compile with checkpointer
memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "hitl-002"}}


# 8. Start workflow
result = graph.invoke(
    {
        "request": "Replace laptop ORD-1001",
        "approved": None,
        "status": "pending"
    },
    config=config
)

print("\nGraph paused:")
print(result)


# 9. Ask human for decision
while True:
    decision = input("\nApprove replacement? (yes/no): ").strip().lower()

    if decision in ("yes", "no"):
        break

    print("Please enter yes or no.")


# 10. Resume graph
result = graph.invoke(
    Command(resume=decision),
    config=config
)

print("\nFinal State:")
print(result)

# poetry run python hitl_lesson2.py
