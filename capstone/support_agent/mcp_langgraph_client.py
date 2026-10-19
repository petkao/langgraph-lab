
import asyncio
import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient


async def main():
    server_path = Path(__file__).resolve().parent / "order_mcp_server.py"

    # Configure the MCP Client
    client = MultiServerMCPClient(
        {
            "orders": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(server_path)],
            }
        }
    )

    # Discover available tools from the MCP Server
    tools = await client.get_tools()

    print("Discovered MCP tools:")

    for tool in tools:
        print(f"Name: {tool.name}")
        print(f"Description: {tool.description}")
        print(f"Input schema: {tool.args_schema}")
        print("-" * 40)


    # Invoke the discovered MCP tool
    order_tool = next(
        tool for tool in tools if tool.name == "get_order"
    )

    result = await order_tool.ainvoke(
        {"order_id": "ORD-1001"}
    )

    print("\nMCP Tool Result:")
    print(result)



if __name__ == "__main__":
    asyncio.run(main())

# poetry run python mcp_langgraph_client.py
