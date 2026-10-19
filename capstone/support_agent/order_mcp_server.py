
from mcp.server.fastmcp import FastMCP

# Create an MCP Server
mcp = FastMCP("Order Support Server")

# Simulated order database
ORDERS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "product": "Laptop",
        "status": "delivered",
        "days_since_delivery": 3,
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "product": "Monitor",
        "status": "shipped",
        "days_since_delivery": None,
    },
}


@mcp.tool()
def get_order(order_id: str) -> dict:
    """Retrieve order information by order ID."""
    return ORDERS.get(
        order_id,
        {"found": False, "order_id": order_id},
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
