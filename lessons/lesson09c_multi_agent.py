from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

load_dotenv()

llm = ChatOpenAI(model="gpt-5.4-mini")

class CustomerServiceState(TypedDict):
    customer_message: str
    intent: str
    response: str

def refund_agent(state: CustomerServiceState):
    customer_message = state["customer_message"]

    result = llm.invoke(
        f"""
        You are a customer service agent specializing in refunds.

        Customer message:
        {customer_message}

        Respond briefly and helpfully.
        Do not claim that a refund has been approved.
        """
    )

    return {
        "response": result.content
    }


def shipping_agent(state: CustomerServiceState):
    customer_message = state["customer_message"]

    result = llm.invoke(
        f"""
        You are a customer service agent specializing in shipping.

        Customer message:
        {customer_message}

        Respond briefly and helpfully.
        Do not invent shipping status or tracking information.
        """
    )

    return {
        "response": result.content
    }

def route_request(state: CustomerServiceState) -> str:
    if state["intent"] == "refund":
        return "refund"

    if state["intent"] == "shipping":
        return "shipping"

    return "unknown"

builder = StateGraph(CustomerServiceState)

builder.add_node("refund_agent", refund_agent)
builder.add_node("shipping_agent", shipping_agent)

builder.add_conditional_edges(
    START,
    route_request,
    {
        "refund": "refund_agent",
        "shipping": "shipping_agent",
        "unknown": END,
    }
)

builder.add_edge("refund_agent", END)
builder.add_edge("shipping_agent", END)

customer_service_graph = builder.compile()

'''
result = customer_service_graph.invoke({
    "customer_message":
        "I bought a laptop yesterday, but I changed my mind. Can I get a refund?",
    "intent": "refund",
    "response": ""
})
'''

result = customer_service_graph.invoke({
    "customer_message":
        "My package hasn't arrived yet. Can you tell me where it is?",
    "intent": "shipping",
    "response": ""
})

print(result)

# poetry run python lessons/lesson09c_multi_agent.py