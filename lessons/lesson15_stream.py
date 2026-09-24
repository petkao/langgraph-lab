from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class WorkState(TypedDict):
    request: str
    research: str
    response: str

def understand_request(state: WorkState):
    print("NODE: understand_request")

    return {
        "research": "Need information about LangGraph streaming"
    }


def retrieve_information(state: WorkState):
    print("NODE: retrieve_information")

    return {
        "research": "LangGraph can stream graph execution events"
    }


def generate_response(state: WorkState):
    print("NODE: generate_response")

    return {
        "response": (
            f"Research result: {state['research']}"
        )
    }

builder = StateGraph(WorkState)

builder.add_node(
    "understand_request",
    understand_request
)

builder.add_node(
    "retrieve_information",
    retrieve_information
)

builder.add_node(
    "generate_response",
    generate_response
)

builder.add_edge(
    START,
    "understand_request"
)

builder.add_edge(
    "understand_request",
    "retrieve_information"
)

builder.add_edge(
    "retrieve_information",
    "generate_response"
)

builder.add_edge(
    "generate_response",
    END
)

graph = builder.compile()

initial_state = {
    "request": "Explain LangGraph streaming",
    "research": "",
    "response": "",
}

print("\n--- USING INVOKE ---")

result = graph.invoke(initial_state)

print("\nFINAL RESULT:")
print(result)

print("\n--- USING STREAM ---")

print("\n--- STREAMING FULL STATE ---")

for state in graph.stream(
    initial_state,
    stream_mode="values",
):
    print("STATE:")
    print(state)



