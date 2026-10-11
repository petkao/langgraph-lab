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

from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

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
    human_approved: bool | None

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
            f"Human approved: {state.get('human_approved')}\n\n"
            f"Policy reason: {state['policy_reason']}\n\n"
            "Explain the decision clearly and politely. "
            "Distinguish policy eligibility from human approval. "
            "If human approval is False, clearly explain that a supervisor "
            "reviewed and declined the replacement request. "
            "Do not say approval is still pending or offer another review. "
            "If human approval is True, explain that a supervisor approved the request, "
            "but do not claim a replacement was processed or shipped. "
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

def human_approval(state: SupportState):
    decision = interrupt({
        "order_id": state["order_id"],
        "product": state["order_data"].get("product"),
        "policy_reason": state["policy_reason"],
        "question": "Do you approve this replacement?"
    })

    return {
        "human_approved": decision["approved"],
        "status": "human_review_completed",
    }

def human_approval(state: SupportState):
    decision = interrupt({
        "order_id": state["order_id"],
        "product": state["order_data"].get("product"),
        "policy_reason": state["policy_reason"],
        "question": "Do you approve this replacement?"
    })

    return {
        "human_approved": decision["approved"],
        "status": "human_review_completed",
    }

def route_after_policy(state: SupportState):
    if state["replacement_eligible"] is True:
        return "human_approval"

    return "replacement_response"    

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
)
builder.add_node("human_approval", human_approval)

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

'''
builder.add_edge(
    "check_replacement_policy",
    "replacement_response",
)
'''

'''
builder.add_edge(
    "check_replacement_policy",
    "human_approval",
)
'''

builder.add_conditional_edges(
    "check_replacement_policy",
    route_after_policy,
    {
        "human_approval": "human_approval",
        "replacement_response": "replacement_response",
    },
)

builder.add_edge(
    "human_approval",
    "replacement_response",
)

builder.add_edge(
    "replacement_response",
    END,
)

# graph = builder.compile()
checkpointer = MemorySaver()

graph = builder.compile(
    checkpointer=checkpointer
)

print("\nGraph structure:")
print(graph.get_graph().draw_ascii())

initial_state = {
    "messages": [
        HumanMessage(
            content=(
                # "The computer I received yesterday won't turn on. "
                "The monitor I received has a problem."
                "Please send me another one. "
                "My order number is ORD-1002."
            )
        )
    ],
    "customer_message": (
        "The monitor I received has a problem. Please send me another one."
        # "The monitor I received has a problem. "
    ),
    "order_id": "ORD-1002",
    "intent": "",
    "status": "",
    "response": "",
    "replacement_eligible": None,
    "policy_reason": "",
    "order_data": {},
    "human_approved": None,
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

config = {
    "configurable": {
        "thread_id": "replacement-demo-001"
    }
}

final_state = graph.invoke(
    initial_state,
    config=config,
)
# result = graph.invoke(initial_state)

print("\nFinal State:")
print(final_state)

if "__interrupt__" in final_state:
    print("\nSupervisor reviews the replacement.")

    resumed_state = graph.invoke(
        Command(resume={"approved": False}),
        config=config,
    )

    print("\nResumed State:")
    print(resumed_state)
else:
    print("\nNo human approval required. Workflow completed.")

# result = graph.invoke(initial_state)

# print("\nFinal State:")
# print(result)

# poetry run python l05_policy_checks.py

