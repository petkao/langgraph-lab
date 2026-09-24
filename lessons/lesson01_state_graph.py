from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# 1. Define the state
class AgentState(TypedDict):
    name: str
    message: str


# 2. Define a node
def create_greeting(state: AgentState):
    name = state["name"]

    return {
        "message": f"Hello {name}, welcome to LangGraph!"
    }

def add_instruction(state: AgentState):
    message = state["message"]

    return {
        "message": message + " Let's learn about state, nodes, and edges."
    }

# 3. Create the graph
builder = StateGraph(AgentState)


# 4. Add the node
builder.add_node("create_greeting", create_greeting)
builder.add_node("add_instruction", add_instruction)


# 5. Define the edges
builder.add_edge(START, "create_greeting")
builder.add_edge("create_greeting", "add_instruction")
builder.add_edge("add_instruction", END)


# 6. Compile the graph
graph = builder.compile()


# 7. Run the graph
result = graph.invoke({
    "name": "Peter",
    "message": ""
})


print(result)

# poetry run python lessons/lesson01_state_graph.py