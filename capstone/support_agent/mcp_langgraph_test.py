
import asyncio
import sys
from pathlib import Path

from langchain_core.messages import AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import ToolNode

from langgraph.graph import StateGraph, MessagesState, START, END

async def main():
    server_path = Path(__file__).resolve().parent / "order_mcp_server.py"

    client = MultiServerMCPClient(
        {
            "orders": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(server_path)],
            }
        }
    )

    tools = await client.get_tools()

    # Create LangGraph ToolNode
    tool_node = ToolNode(tools)

    # Build a simple LangGraph workflow
    builder = StateGraph(MessagesState)

    builder.add_node("tools", tool_node)

    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)

    graph = builder.compile()

    # Simulate an LLM requesting the MCP tool
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_order",
                "args": {"order_id": "ORD-1001"},
                "id": "call_001",
                "type": "tool_call",
            }
        ],
    )

    # Execute through the compiled LangGraph
    result = await graph.ainvoke(
        {"messages": [message]}
    )

    print("\nLangGraph MCP Result:")

    for msg in result["messages"]:
        print(f"{msg.type}: {msg.content}")

if __name__ == "__main__":
    asyncio.run(main())

# poetry run python mcp_langgraph_test.py
