import json
from dotenv import load_dotenv
from typing import TypedDict, Literal

from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import RetryPolicy

lookup_attempts = 0

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
    replacement_eligible: bool | None
    policy_reason: str
    order_data: dict

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

def lookup_order(state: SupportState):
    global lookup_attempts

    lookup_attempts += 1
    print(f"Order lookup attempt: {lookup_attempts}")

    if lookup_attempts <= 3:
        print("Simulating invalid order lookup request failure...")
        raise ValueError("Invalid order lookup request")

    order_data = get_order.invoke({
        "order_id": state["order_id"]
    })

    return {
        "order_data": order_data,
        "status": "order_lookup_completed",
    }

def check_replacement_policy(state: SupportState):
    # order = ORDERS.get(state["order_id"])
    order = state["order_data"]

    #if order is None:
    if not order.get("found"):
        return {
            "replacement_eligible": False,
            "policy_reason": "Order not found.",
            "status": "policy_checked",
        }

    if order["status"] != "delivered":
        return {
            "replacement_eligible": False,
            "policy_reason": "Order has not been delivered.",
            "status": "policy_checked",
        }

    if order["days_since_delivery"] > 30:
        return {
            "replacement_eligible": False,
            "policy_reason": "Order is outside the 30-day replacement window.",
            "status": "policy_checked",
        }

    return {
        "replacement_eligible": True,
        "policy_reason": "Order is within the 30-day replacement window.",
        "status": "policy_checked",
    }

def replacement_response(state: SupportState):
    policy_context = SystemMessage(
        content=(
            "You are a customer support response agent. "
            "The order information and policy decision below are authoritative.\n\n"
            f"Order data: {state['order_data']}\n"
            f"Replacement eligible: {state['replacement_eligible']}\n"
            f"Policy reason: {state['policy_reason']}\n\n"
            "Explain the decision clearly and politely. "
            "Do not invent procedures, timelines, shipping arrangements, fees, "
            "approvals, or actions that are not provided."
        )
    )

    response = model.invoke(
        [policy_context] + state["messages"]
    )

    return {
        "messages": [response],
        "response": response.content,
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

'''
def replacement_llm(state: SupportState):
    if state["replacement_eligible"] is None:
        policy_text = (
            "Replacement eligibility has not been checked yet. "
            "Use the available tools to gather the information needed. "
            "Do not tell the customer that a replacement is approved."
        )
    else:
        policy_text = (
            f"Replacement eligible: {state['replacement_eligible']}. "
            f"Policy reason: {state['policy_reason']} "
            "Follow this policy result. "
            "Do not invent additional policies, procedures, timelines, fees, "
            "shipping arrangements, or actions."
        )

    policy_context = SystemMessage(
        content=(
            "You are a customer support replacement agent. "
            "You may use available tools to obtain order information. "
            f"{policy_text}"
        )
    )

    response = replacement_model.invoke(
        [policy_context] + state["messages"]
    )

    return {
        "messages": [response],
    }  
'''  

def replacement_llm(state: SupportState):
    system_message = SystemMessage(
        content=(
            "You are a customer support replacement agent. "
            "Use the available tools to obtain order information needed "
            "to evaluate the customer's replacement request. "
            "Do not decide replacement eligibility yourself. "
            "Do not promise or perform a replacement."
        )
    )

    response = replacement_model.invoke(
        [system_message] + state["messages"]
    )

    return {
        "messages": [response],
    }

def store_order_data(state: SupportState):
    last_message = state["messages"][-1]

    order_data = json.loads(last_message.content)

    return {
        "order_data": order_data,
        "status": "order_data_stored",
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
# builder.add_node("replacement_llm", replacement_llm)
# builder.add_node("replacement_tools", replacement_tools)
builder.add_node(
    "check_replacement_policy",
    check_replacement_policy,
)

'''
builder.add_node(
    "store_order_data",
    store_order_data,
)
'''

builder.add_node(
    "replacement_response",
    replacement_response,
)

builder.add_node(
    "lookup_order",
    lookup_order,
    retry_policy=RetryPolicy(
        max_attempts=3,
        retry_on=ConnectionError,
        initial_interval=0.5,
    ),
)

builder.add_edge(START, "receive_request")
builder.add_edge("receive_request", "understand_request")
builder.add_conditional_edges(
    "understand_request",
    route_by_intent,
    {
        # "replacement": "replacement_llm",
        "replacement": "lookup_order",
        "refund": "refund_agent",
        "general_support": "general_support_agent",
    }
)

'''
builder.add_conditional_edges(
    "replacement_llm",
    tools_condition,
    {
        "tools": "replacement_tools",
        END: END,
    }
)
'''

# builder.add_edge("replacement_agent", END)
builder.add_edge("refund_agent", END)
builder.add_edge("general_support_agent", END)

'''
builder.add_edge(
    "replacement_tools",
    "replacement_llm",
)
'''

'''
builder.add_edge(
    "replacement_tools",
    "store_order_data",
)
'''

builder.add_edge(
    "lookup_order",
    "check_replacement_policy",
)

'''
builder.add_edge(
    "store_order_data",
    "check_replacement_policy",
)
'''

builder.add_edge(
    "check_replacement_policy",
    "replacement_response",
)

builder.add_edge(
    "replacement_response",
    END,
)

graph = builder.compile()

print("\nGraph structure:")
print(graph.get_graph().draw_ascii())

initial_state = {
    "messages": [
        HumanMessage(
            content=(
                "The computer I received yesterday won't turn on. "
                # "The monitor I received has a problem."
                "Please send me another one. "
                "My order number is ORD-1001."
            )
        )
    ],
    "customer_message": (
        "The computer I received yesterday won't turn on. "
        # "The monitor I received has a problem. "
        "Please send me another one."
    ),
    "order_id": "ORD-1001",
    "intent": "",
    "status": "",
    "response": "",
    "replacement_eligible": None,
    "policy_reason": "",
    "order_data": {},
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

try:
    result = graph.invoke(initial_state)

except ConnectionError as error:
    print("\nOrder lookup failed after retries.")
    print(f"Error: {error}")
    print("Please try again later.")
    result = None

except ValueError as error:
    print("\nInvalid order lookup request.")
    print(f"Error: {error}")
    print("Please check the order information.")
    result = None

print("\nFinal State:")
print(result)

# result = graph.invoke(initial_state)

# print("\nFinal State:")
# print(result)

# poetry run python l07_error_handling.py

