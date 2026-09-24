from typing import TypedDict, Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from langchain_openai import ChatOpenAI
from pathlib import Path
from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_FILE)

llm = ChatOpenAI(
    model="gpt-5.4-mini"
)

class CustomerServiceState(TypedDict):
    actor_id: str
    customer_message: str
    messages: Annotated[list[AnyMessage], add_messages]
    intent: str
    order_id: str
    refund_id: str
    refund_amount: float
    response: str

class ShippingState(TypedDict):
    actor_id: str
    order_id: str
    messages: Annotated[
        list[AnyMessage],
        add_messages
    ]
    shipment_status: str


class RefundState(TypedDict):
    actor_id: str
    order_id: str
    refund_id: str
    refund_amount: float
    approval_status: str
    result: str

# -------------------------------------------------
# Shipping capability
# -------------------------------------------------

def get_shipment_status(actor_id: str, order_id: str):
    """
    Simulated authoritative shipping capability.
    """

    orders = {
        "ORD-123": {
            "customer_id": "CUST-100",
            "status": "in transit",
        },
        "ORD-456": {
            "customer_id": "CUST-200",
            "status": "delivered",
        },
    }

    order = orders.get(order_id)

    if order is None:
        return {
            "status": "not_found"
        }

    if order["customer_id"] != actor_id:
        return {
            "status": "unauthorized"
        }

    return {
        "status": order["status"]
    }

# -------------------------------------------------
# Shipping subgraph
# -------------------------------------------------

def check_shipping(state: ShippingState):

    shipment = get_shipment_status(
        actor_id=state["actor_id"],
        order_id=state["order_id"],
    )

    return {
        "shipment_status": shipment["status"]
    }

shipping_builder = StateGraph(ShippingState)

shipping_builder.add_node(
    "check_shipping",
    check_shipping
)

shipping_builder.add_edge(
    START,
    "check_shipping"
)

shipping_builder.add_edge(
    "check_shipping",
    END
)

shipping_graph = shipping_builder.compile()

def shipping_adapter(state: CustomerServiceState):

    shipping_input = {
        "actor_id": state["actor_id"],
        "order_id": state["order_id"],
        "messages": state["messages"],
        "shipment_status": "",
    }

    shipping_result = shipping_graph.invoke(
        shipping_input
    )

    status = shipping_result["shipment_status"]

    if status == "unauthorized":
        response = "Unable to access that order."
    elif status == "not_found":
        response = "Unable to find that order."
    else:
        response = (
            f"Order {state['order_id']} is {status}."
        )

    return {
        "response": response
    }

# -------------------------------------------------
# Refund capability
# -------------------------------------------------

def get_refund_eligibility(
    actor_id: str,
    order_id: str,
    refund_amount: float,
):

    orders = {
        "ORD-123": {
            "customer_id": "CUST-100",
            "amount_paid": 1500.00,
            "already_refunded": False,
        },
        "ORD-456": {
            "customer_id": "CUST-200",
            "amount_paid": 200.00,
            "already_refunded": False,
        },
    }

    order = orders.get(order_id)

    if order is None:
        return {
            "status": "not_found"
        }

    if order["customer_id"] != actor_id:
        return {
            "status": "unauthorized"
        }

    if order["already_refunded"]:
        return {
            "status": "already_refunded"
        }

    if refund_amount <= 0:
        return {
            "status": "invalid_amount"
        }

    if refund_amount > order["amount_paid"]:
        return {
            "status": "amount_exceeds_payment"
        }

    return {
        "status": "eligible"
    }

# -------------------------------------------------
# Refund subgraph
# -------------------------------------------------

def check_refund_eligibility(state: RefundState):

    result = get_refund_eligibility(
        actor_id=state["actor_id"],
        order_id=state["order_id"],
        refund_amount=state["refund_amount"],
    )

    return {
        "result": result["status"]
    }

def route_refund_eligibility(state: RefundState):

    if state["result"] == "eligible":
        return "eligible"

    return "denied"

def evaluate_refund_approval(state: RefundState):

    if state["refund_amount"] <= 500:
        return {
            "approval_status": "automatic"
        }

    return {
        "approval_status": "human_required"
    }


def refund_denied(state: RefundState):

    return {
        "approval_status": "denied"
    }

def request_human_approval(state: RefundState):

    decision = interrupt(
        {
            "order_id": state["order_id"],
            "refund_amount": state["refund_amount"],
            "message": "Human approval required",
        }
    )

    return {
        "approval_status": decision
    }

def route_approval_requirement(state: RefundState):

    if state["approval_status"] == "automatic":
        return "automatic"

    if state["approval_status"] == "human_required":
        return "human"

    return "invalid"

def execute_refund(
    actor_id: str,
    order_id: str,
    refund_id: str,
    refund_amount: float,
):
    # Training simulation of an authoritative refund service.
    return {
        "status": "completed",
        "refund_id": refund_id,
        "amount": refund_amount,
    }

def process_refund(state: RefundState):

    result = execute_refund(
        actor_id=state["actor_id"],
        order_id=state["order_id"],
        refund_id=state["refund_id"],
        refund_amount=state["refund_amount"],
    )

    return {
        "result": result["status"]
    }

def reject_refund(state: RefundState):
    return {
        "result": "Refund rejected by human reviewer"
    }

def invalid_human_decision(state: RefundState):
    return {
        "result": "Invalid human decision. Workflow stopped."
    }

def invalid_approval(state: RefundState):
    return {
        "result": "Invalid approval state. Workflow stopped."
    }

def route_human_decision(state: RefundState):

    if state["approval_status"] == "approved":
        return "approved"

    if state["approval_status"] == "rejected":
        return "rejected"

    return "invalid"

refund_builder = StateGraph(RefundState)

refund_builder.add_node(
    "check_refund_eligibility",
    check_refund_eligibility
)

refund_builder.add_node(
    "evaluate_refund_approval",
    evaluate_refund_approval
)

refund_builder.add_node(
    "refund_denied",
    refund_denied
)

refund_builder.add_node(
    "request_human_approval",
    request_human_approval
)

refund_builder.add_node(
    "process_refund",
    process_refund
)

refund_builder.add_node(
    "invalid_approval",
    invalid_approval
)

refund_builder.add_node(
    "reject_refund",
    reject_refund
)

refund_builder.add_node(
    "invalid_human_decision",
    invalid_human_decision
)

refund_builder.add_edge(
    START,
    "check_refund_eligibility"
)

refund_builder.add_conditional_edges(
    "check_refund_eligibility",
    route_refund_eligibility,
    {
        "eligible": "evaluate_refund_approval",
        "denied": "refund_denied",
    }
)

refund_builder.add_conditional_edges(
    "evaluate_refund_approval",
    route_approval_requirement,
    {
        "automatic": "process_refund",
        "human": "request_human_approval",
        "invalid": "invalid_approval",
    }
)

refund_builder.add_conditional_edges(
    "request_human_approval",
    route_human_decision,
    {
        "approved": "process_refund",
        "rejected": "reject_refund",
        "invalid": "invalid_human_decision",
    }
)

refund_builder.add_edge(
    "reject_refund",
    END
)

refund_builder.add_edge(
    "invalid_human_decision",
    END
)

refund_builder.add_edge(
    "process_refund",
    END
)

refund_builder.add_edge(
    "invalid_approval",
    END
)

refund_builder.add_edge(
    "refund_denied",
    END
)

DB_URI = "postgresql://tzechungkao@localhost:5432/langgraph_lab"

pool = ConnectionPool(
    conninfo=DB_URI,
    max_size=10,
    open=False,
    kwargs={
        "autocommit": True,
        "prepare_threshold": 0,
    },
)

checkpointer = PostgresSaver(pool)

refund_graph = refund_builder.compile(
    checkpointer=checkpointer
)

def refund_adapter(state: CustomerServiceState):

    refund_input = {
        "actor_id": state["actor_id"],
        "order_id": state["order_id"],
        "refund_id": state["refund_id"],
        "refund_amount": state["refund_amount"],
        "approval_status": "",
        "result": "",
    }

    config = {
        "configurable": {
            "thread_id": f"refund-{state['refund_id']}"
        }
    }

    refund_result = refund_graph.invoke(
        refund_input,
        config=config,
    )

    if "__interrupt__" in refund_result:
        return {
            "response": "Refund requires human approval."
        }

    return {
        "response": refund_result["result"]
    }

def understand_intent(state: CustomerServiceState):

    result = llm.invoke(
        [
            {
                "role": "system",
                "content": (
                    "Classify the customer's request. "
                    "Return exactly one word: "
                    "shipping, refund, or unknown."
                ),
            },
            {
                "role": "user",
                "content": state["customer_message"],
            },
        ]
    )

    intent = result.content.strip().lower()

    allowed_intents = {
        "shipping",
        "refund",
        "unknown",
    }

    if intent not in allowed_intents:
        intent = "unknown"

    return {"intent": intent}

def route_customer_request(state: CustomerServiceState):

    if state["intent"] == "shipping":
        return "shipping"

    if state["intent"] == "refund":
        return "refund"

    return "unknown"

def handle_unknown(state: CustomerServiceState):

    return {
        "response": (
            "I can only help with shipping "
            "or refund requests."
        )
    }

parent_builder = StateGraph(CustomerServiceState)

parent_builder.add_node(
    "shipping_adapter",
    shipping_adapter
)

parent_builder.add_node(
    "refund_adapter",
    refund_adapter
)

parent_builder.add_node(
    "handle_unknown",
    handle_unknown
)

parent_builder.add_node(
    "understand_intent",
    understand_intent
)

parent_builder.add_edge(
    START,
    "understand_intent"
)

parent_builder.add_conditional_edges(
    "understand_intent",
    route_customer_request,
    {
        "shipping": "shipping_adapter",
        "refund": "refund_adapter",
        "unknown": "handle_unknown",
    }
)

parent_builder.add_edge(
    "shipping_adapter",
    END
)

parent_builder.add_edge(
    "refund_adapter",
    END
)

parent_builder.add_edge(
    "handle_unknown",
    END
)

parent_graph = parent_builder.compile()

# print(parent_graph.get_graph().draw_mermaid())

# print(refund_graph.get_graph().draw_mermaid())

if __name__ == "__main__":

    pool.open()
    pool.wait()

    result = parent_graph.invoke({
        "actor_id": "CUST-100",
        "customer_message": "I want a $200 refund for my order.",
        "messages": [],
        "intent": "",
        "order_id": "ORD-123",
        "refund_id": "REF-003",
        "refund_amount": 200.0,
        "response": "",
    })

    print(result)

    pool.close()

'''
if __name__ == "__main__":

    pool.open()
    pool.wait()

    result = refund_adapter(
        {
            "actor_id": "CUST-100",
            "customer_message": "Please refund $200.",
            "messages": [],
            "intent": "refund",
            "order_id": "ORD-123",
            "refund_id": "REF-002",
            "refund_amount": 200.00,
            "response": "",
        }
    )

    print(result)

    pool.close()
'''

'''
if __name__ == "__main__":

    pool.open()
    pool.wait()

    config = {
        "configurable": {
            "thread_id": "lesson18-refund-002"
        }
    }

    result = refund_graph.invoke(
        {
            "actor_id": "CUST-100",
            "order_id": "ORD-123",
            "refund_amount": 1200.00,
            "approval_status": "",
            "result": "",
        },
        config=config,
    )

    print(result)

    pool.close()
'''

'''
if __name__ == "__main__":

    result = shipping_adapter(
        {
            "actor_id": "CUST-100",
            "customer_message": "Where is my order?",
            "messages": [],
            "intent": "shipping",
            "order_id": "ORD-123",
            "refund_amount": 0.0,
            "response": "",
        }
    )

    print(result)
'''

# poetry run python -m lessons.lesson18_capstone
