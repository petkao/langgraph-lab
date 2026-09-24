from dotenv import load_dotenv

from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

load_dotenv()

class AgentState(TypedDict):
    user_message: str
    intent: str
    response: str

llm = ChatOpenAI(
    model="gpt-5.4-mini"
)

def understand_request(state: AgentState):
    user_message = state["user_message"]

    response = llm.invoke(
        f"""
        Determine the customer's intent.

        Customer message:
        {user_message}

        Return only one of:
        refund
        shipping
        product_question
        other
        """
    )

    return {
        "intent": response.content.strip()
    }

def handle_refund(state: AgentState):
    return {
        "response": "I can help you with your refund."
    }


def handle_shipping(state: AgentState):
    return {
        "response": "I can help you with your shipping question."
    }


def handle_general(state: AgentState):
    return {
        "response": "I can help you with your question."
    }

def route_intent(state: AgentState) -> str:
    return state["intent"]

builder = StateGraph(AgentState)

builder.add_node(
    "understand_request",
    understand_request
)

builder.add_node(
    "handle_refund",
    handle_refund
)

builder.add_node(
    "handle_shipping",
    handle_shipping
)

builder.add_node(
    "handle_general",
    handle_general
)

builder.add_edge(START, "understand_request")
builder.add_conditional_edges(
    "understand_request",
    route_intent,
    {
        "refund": "handle_refund",
        "shipping": "handle_shipping",
        "product_question": "handle_general",
        "other": "handle_general",
    }
)

builder.add_edge("handle_refund", END)
builder.add_edge("handle_shipping", END)
builder.add_edge("handle_general", END)

graph = builder.compile()

result = graph.invoke({
    "user_message": (
        "I bought this laptop yesterday but changed my mind. "
        "Can I get my money back?"
    ),
    "intent": "",
    "response": ""
})

print(result)





