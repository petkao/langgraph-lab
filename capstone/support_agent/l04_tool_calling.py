from dotenv import load_dotenv
from typing import TypedDict, Literal

from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

class IntentClassification(BaseModel):
    intent: Literal[
        "replacement",
        "refund",
        "general_support"
    ]   

load_dotenv()

model = ChatOpenAI(
    model = "gpt-5-mini",
    temperature=0
)

intent_model = model.with_structured_output(IntentClassification)

class SupportState(MessagesState):
    customer_message: str
    order_id: str
    intent: str
    status: str
    response: str

ORDERS = {
    "ORD-1001": {
        "product": "Laptop",
        "status": "delivered",
        "days_since_delivery": 3,
    },
    "ORD-1002": {
        "product": "Monitor",
        "status": "delivered",
        "days_since_delivery": 45,
    },
}

@tool
def get_order(order_id: str) -> dict:
    """Look up an order using its order ID."""

    order = ORDERS.get(order_id)
    
    if order is None:
        return {
            "found": False,
            "order_id": order_id,
        }

    return {
        "found": True,
        "order_id": order_id,
        **order,
    }

replacement_model = model.bind_tools([get_order])
replacement_tools = ToolNode([get_order])

def receive_request(state: SupportState):
    print(f"Customer: {state["customer_message"]}")

    return {
        "status": "request_received"
    }

def understand_request(state: SupportState):
   classification = intent_model.invoke(
    [
        (
            "system",
            """
            You are an intent classification agent for a customer support system.

            Your role is to analyze the customer's message and determine
            which support workflow should handle the request.

            You do not answer the customer's question.
            You do not perform refunds or replacements.
            You only classify the customer's primary intent.

            Classify the request into exactly one of these intents:

            - replacement: the customer wants an item replaced
            - refund: the customer wants their money returned
            - general_support: any other support request

            Choose the intent based on the meaning of the customer's request,
            not just specific keywords.            """,
        ),
        ("human",state["customer_message"])
    ]
   )
   return {
    "intent": classification.intent,
    "status": "request_understood",
   }

def replacement_agent(state: SupportState):
    order_result = get_order.invoke(
        {"order_id": state["order_id"]}
    )

    if not order_result["found"]:
        return {
            "response": "I could not find that order.",
            "status": "order_not_found",
        }

    return {
        "response": (
            f"Order {order_result["order_id"]} was found. "
            f"Product: {order_result["product"]}. "
            f"Status: {order_result["status"]}. "
        ),
        "status": "order_found",
    }

def replacement_llm(state: SupportState):
    response = replacement_model.invoke(state["messages"])  
    return {
        "messages": [response],
    }

def refund_agent(state: SupportState):
    return {
        "response": "Let me check whether this order is eligible for a refund.",
        "status": "refund_agent"
    }

def general_support_agent(state: SupportState):
    return {
        "response": "Let me help you with your support question.",
        "status": "general_support_agent"
    }

def route_by_intent(state: SupportState):
    return state["intent"]



builder = StateGraph(SupportState)

builder.add_node("receive_request", receive_request)
builder.add_node("understand_request", understand_request)
builder.add_node("general_support_agent", general_support_agent)
# builder.add_node("replacement_agent",replacement_agent)
builder.add_node("refund_agent", refund_agent)
builder.add_node("replacement_llm", replacement_llm)
builder.add_node("replacement_tools", replacement_tools)


builder.add_edge(START, "receive_request")
builder.add_edge("receive_request", "understand_request")
builder.add_conditional_edges(
    "understand_request",
    route_by_intent,
    {
        "replacement": "replacement_llm",
        "refund": "refund_agent",
        "general_support": "general_support_agent",
    }
)
builder.add_conditional_edges(
    "replacement_llm",
    tools_condition,
    {
        "tools": "replacement_tools",
        END: END,
    }
)

# builder.add_edge("replacement_agent", END)
builder.add_edge("refund_agent", END)
builder.add_edge("general_support_agent", END)
builder.add_edge(
    "replacement_tools",
    "replacement_llm",
)

graph = builder.compile()

initial_state = {
    "messages": [
        HumanMessage(
            content=(
                "The computer I received yesterday won't turn on. "
                "Please send me another one. "
                "My order number is ORD-1001."
            )
        )
    ],
    "customer_message": (
        "The computer I received yesterday won't turn on. "
        "Please send me another one."
    ),
    "order_id": "ORD-1001",
    "intent": "",
    "status": "",
    "response": "",
}

'''
test_message = HumanMessage(
    content="Please check order ORD-1001. My laptop arrived damaged."
)

ai_message = replacement_model.invoke([test_message])

print("\nLLM Response:")
print(ai_message)

print("\nTool Calls:")
print(ai_message.tool_calls)

tool_call = ai_message.tool_calls[0]

tool_result = get_order.invoke(tool_call["args"])

print("\nTool Result:")
print(tool_result)

tool_message = ToolMessage(
    content=str(tool_result),
    tool_call_id=tool_call["id"],
)

print("\nTool Message:")
print(tool_message)


final_message = replacement_model.invoke(
    [
        test_message,
        ai_message,
        tool_message,
    ]
)


print("\nFinal LLM Response:")
print(final_message.content)
'''

result = graph.invoke(initial_state)

print("\nFinal State:")
print(result)

# result = graph.invoke(initial_state)

# print("\nFinal State:")
# print(result)

# poetry run python l04_tool_calling.py






