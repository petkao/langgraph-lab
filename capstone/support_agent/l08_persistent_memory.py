import json
from dotenv import load_dotenv
from typing import TypedDict, Literal

from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import RetryPolicy
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from typing import Annotated
import uuid

# thread_id = str(uuid.uuid4())

lookup_attempts = 0

class IntentClassification(BaseModel):
    intent: Literal[
        "replacement",
        "refund",
        "general_support"
    ]  

class FollowUpClassification(BaseModel):
    decision: Literal[
        "confirm",
        "decline",
        "question"
    ] 

load_dotenv()

model = ChatOpenAI(
    model = "gpt-5-mini",
    temperature=0
)

intent_model = model.with_structured_output(IntentClassification)
follow_up_model = model.with_structured_output(FollowUpClassification)

class SupportState(MessagesState):
    messages: Annotated[list, add_messages]
    customer_message: str
    order_id: str
    intent: str
    status: str
    response: str
    replacement_eligible: bool | None
    policy_reason: str
    order_data: dict
    workflow_stage: str

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

    # if lookup_attempts <= 3:
        # print("Simulating invalid order lookup request failure...")
        # raise ValueError("Invalid order lookup request")

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
        "workflow_stage": (
            "awaiting_confirmation"
            if state["replacement_eligible"]
            else "completed"
        ),
    }

replacement_model = model.bind_tools([get_order])
replacement_tools = ToolNode([get_order])

def receive_request(state: SupportState):
    print(f"Customer: {state['messages'][-1].content}")

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
        ("human", state["messages"][-1].content)
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

def handle_follow_up(state: SupportState):
    reply = "Your follow-up has been received."

    classification = follow_up_model.invoke([
        (
            "system",
            "Classify the customer's response to a replacement request. "
            "Return confirm if the customer clearly agrees, "
            "decline if the customer refuses or cancels, "
            "or question if the decision is unclear."
        ),
        ("human", state["messages"][-1].content)
    ])

    print("Follow-up Decision:", classification.decision)

    if (
        classification.decision == "confirm"
        and state["replacement_eligible"] is True
        and state["workflow_stage"] == "awaiting_confirmation"
    ):
        return {
            "messages": [
                AIMessage(
                    content="Thank you for confirming. Your replacement request is ready for the next processing step."
                )
            ],
            "response": "Thank you for confirming. Your replacement request is ready for the next processing step.",
            "status": "confirmation_received",
            "workflow_stage": "confirmation_received",
        }
    
    if (
        classification.decision == "decline"
        and state["workflow_stage"] == "awaiting_confirmation"
    ):
        return {
            "messages": [
                AIMessage(
                    content="I understand. Your replacement request has been cancelled."
                )
            ],
            "response": "I understand. Your replacement request has been cancelled.",
            "status": "replacement_cancelled",
            "workflow_stage": "replacement_cancelled",
        }

    return {
        "messages": [AIMessage(content=reply)],
        "response": reply,
        "status": "follow_up_received",
    }

def route_conversation(state: SupportState):
    if state.get("workflow_stage") == "awaiting_confirmation":
        return "follow_up"

    return "new_request"

def route_by_intent(state: SupportState):
    return state["intent"]

builder = StateGraph(SupportState)

builder.add_node("receive_request", receive_request)
builder.add_node("understand_request", understand_request)
builder.add_node("handle_follow_up", handle_follow_up)
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
# builder.add_edge("receive_request", "understand_request")
builder.add_conditional_edges(
    "receive_request",
    route_conversation,
    {
        "new_request": "understand_request",
        "follow_up": "handle_follow_up",
    }
)
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
builder.add_edge("handle_follow_up", END)

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

# graph = builder.compile()
# memory = MemorySaver()
# graph = builder.compile(checkpointer=memory)
import sqlite3

conn = sqlite3.connect(
    "customer_memory.db",
    check_same_thread=False
)

print("SQLite location:", conn.execute("PRAGMA database_list").fetchall())

print("SQLite database connected successfully")
print("Database location:", conn.execute("PRAGMA database_list").fetchall())

memory = SqliteSaver(conn)
memory.setup()

print("Checkpoint type:", type(memory).__name__)
graph = builder.compile(checkpointer=memory)

if __name__ == "__main__":

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
        "workflow_stage": "new_request",
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
        config = {
            "configurable": {
                "thread_id": "customer-002"
            }
        }

        result = graph.invoke(initial_state, config=config)

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

    print("\nSaved Conversation State:")

    print("\nCustomer Follow-up:")
    follow_up = "Yes, I want the replacement. My shipping address is correct."
    print(follow_up)

    follow_up_result = graph.invoke(
        {"messages": [HumanMessage(content=follow_up)]},
        config=config
    )

    print("\nProcessing Customer Follow-up:")
    print("Follow-up Status:", follow_up_result["status"])
    print("Follow-up Response:", follow_up_result["response"])

    snapshot = graph.get_state(config)

    print("Thread ID:", config["configurable"]["thread_id"])
    print("Saved Order ID:", snapshot.values.get("order_id"))
    print("Saved Intent:", snapshot.values.get("intent"))
    print("Saved Workflow Stage:", snapshot.values.get("workflow_stage"))
    print("Saved Messages:", len(snapshot.values.get("messages", [])))

    print("\nConversation History:")

    for message in snapshot.values.get("messages", []):
        print(f"{message.type}: {message.content}")

    print("\n=== Testing Multiple Customer Threads ===")

    config_001 = {
        "configurable": {"thread_id": "customer-001"}
    }

    config_002 = {
        "configurable": {"thread_id": "customer-002"}
    }

    # Start a new conversation for customer-001
    customer_001_state = dict(initial_state)
    customer_001_state["messages"] = [
        HumanMessage(
        content="My laptop is defective. Please replace it. Order ORD-1001."
    )
    ]
    customer_001_state["workflow_stage"] = "new_request"

    graph.invoke(customer_001_state, config=config_001)

    # Inspect both customers' saved states
    snapshot_001 = graph.get_state(config_001)
    snapshot_002 = graph.get_state(config_002)

    print("\nCustomer 001:")
    print("Order:", snapshot_001.values["order_id"])
    print("Stage:", snapshot_001.values["workflow_stage"])
    print("Status:", snapshot_001.values.get("status"))
    print("Intent:", snapshot_001.values.get("intent"))
    print("Messages:", len(snapshot_001.values["messages"]))

    print("\nCustomer 002:")
    print("Order:", snapshot_002.values["order_id"])
    print("Stage:", snapshot_002.values["workflow_stage"])
    print("Messages:", len(snapshot_002.values["messages"]))

    print("\n=== SQLite Memory Recovery Test ===")

    recovery_config = {
        "configurable": {"thread_id": "customer-002"}
    }

    recovered = graph.get_state(recovery_config)

    print("Recovered Order:", recovered.values["order_id"])
    print("Recovered Stage:", recovered.values["workflow_stage"])
    print("Recovered Messages:", len(recovered.values["messages"]))

    # result = graph.invoke(initial_state)

    # print("\nFinal State:")
    # print(result)

    # poetry run python l08_persistent_memory.py

# poetry run python -c "from l08_persistent_memory import graph; print('LangGraph imported successfully!')"