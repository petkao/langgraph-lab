
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver


# 1. Define graph state
class AgentState(TypedDict):
    request: str
    approved: bool | None


# 2. Define the approval node
def request_approval(state: AgentState):
    print("Request:", state["request"])

    decision = interrupt({
        "question": "Do you approve this request?",
        "request": state["request"]
    })

    print("Human decision:", decision)

    return {"approved": decision == "yes"}


# 3. Build graph
builder = StateGraph(AgentState)

builder.add_node("request_approval", request_approval)

builder.add_edge(START, "request_approval")
builder.add_edge("request_approval", END)


# 4. Compile with checkpointer
memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)


# 5. Define thread
config = {"configurable": {"thread_id": "hitl-001"}}


# 6. Start graph
result = graph.invoke(
    {
        "request": "Replace laptop ORD-1001",
        "approved": None
    },
    config=config
)

print("\nFirst result:")
print(result)

snapshot = graph.get_state(config)

print("\nCheckpoint State:")
print("Values:", snapshot.values)
print("Next:", snapshot.next)
print("Interrupts:", snapshot.interrupts)

# 7. Simulate human approval
result = graph.invoke(
    Command(resume="yes"),
    config=config
)

print("\nFinal result:")
print(result)

# poetry run python hitl_lesson1.py