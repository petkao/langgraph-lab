from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class ShippingState(TypedDict):
    order_id: str
    shipping_address: str
    shipment_status: str


class CustomerServiceState(TypedDict):
    actor_id: str
    order_id: str
    shipping_address: str
    customer_message: str

    payment_token: str
    fraud_notes: str

    response: str

def get_shipment_status(order_id: str):
    print(f"Shipping capability checking {order_id}")

    # Simulated authoritative system
    return {
        "order_id": order_id,
        "status": "in transit"
    }

def check_shipping(state: ShippingState):

    print("\n--- INSIDE SHIPPING SUBGRAPH ---")
    print("Shipping state:", state)

    shipment = get_shipment_status(
        state["order_id"]
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

    print("\n--- PARENT STATE BEFORE ADAPTER ---")
    print(state)

    shipping_input = {
        "order_id": state["order_id"],
        "shipping_address": state["shipping_address"],
        "shipment_status": "",
    }

    print("\n--- DATA PASSED TO SUBGRAPH ---")
    print(shipping_input)

    shipping_result = shipping_graph.invoke(
        shipping_input
    )

    print("\n--- RESULT FROM SUBGRAPH ---")
    print(shipping_result)

    return {
        "response": (
            f"Order {state['order_id']} is "
            f"{shipping_result['shipment_status']}"
        )
    }


parent_builder = StateGraph(CustomerServiceState)

parent_builder.add_node(
    "shipping_adapter",
    shipping_adapter
)

parent_builder.add_edge(
    START,
    "shipping_adapter"
)

parent_builder.add_edge(
    "shipping_adapter",
    END
)

parent_graph = parent_builder.compile()

result = parent_graph.invoke(
    {
        "actor_id": "CUST-100",
        "order_id": "ORD-123",
        "shipping_address": "123 Main Street",
        "customer_message": "Where is my order?",
        "payment_token": "SECRET-PAYMENT-TOKEN",
        "fraud_notes": "INTERNAL-ONLY",
        "response": "",
    }
)

print("\n--- FINAL PARENT STATE ---")
print(result)




