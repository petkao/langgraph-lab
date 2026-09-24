from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    name: str
    level: str
    message: str

def check_level(state: AgentState):
    print(f"Checking level: {state['level']}")

    return {}


def beginner_message(state: AgentState):
    return {
        "message": f"Hello {state['name']}. Let's start with LangGraph basics."
    }


def advanced_message(state: AgentState):
    return {
        "message": f"Hello {state['name']}. Let's study advanced LangGraph."
    }

def route_by_level(state: AgentState):
    if state["level"] == "beginner":
        return "beginner"

    return "advanced"

builder = StateGraph(AgentState)

builder.add_node("check_level", check_level)
builder.add_node("beginner_message", beginner_message)
builder.add_node("advanced_message", advanced_message)

builder.add_edge(START, "check_level")

builder.add_conditional_edges(
    "check_level",
    route_by_level,
    {
        "beginner": "beginner_message",
        "advanced": "advanced_message",
    }
)

builder.add_edge("beginner_message", END)
builder.add_edge("advanced_message", END)

graph = builder.compile()

result = graph.invoke({
    "name": "Peter",
    "level": "beginner",
    "message": ""
})

print(result)

# poetry run python lessons/lesson02_conditional_edges.py