
import asyncio
import sys
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from dotenv import load_dotenv
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")

async def main():
    server_path = Path(__file__).resolve().parent / "order_mcp_server.py"

    # 1. Connect to MCP Server
    client = MultiServerMCPClient(
        {
            "orders": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(server_path)],
            }
        }
    )

    # 2. Discover MCP tools
    tools = await client.get_tools()

    print("Available MCP tools:", [tool.name for tool in tools])

    # 3. Bind MCP tools to the LLM
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0)
    llm_with_tools = llm.bind_tools(tools)

    # 4. Define the agent node
    async def agent(state: MessagesState):
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    # 5. Build LangGraph
    builder = StateGraph(MessagesState)

    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "agent")

    builder.add_conditional_edges(
        "agent",
        tools_condition,
    )

    builder.add_edge("tools", "agent")

    graph = builder.compile()

    # 6. Ask a customer question
    result = await graph.ainvoke(
        {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a customer support assistant. "
                        "Use the available order tool to look up "
                        "order information. Never invent order details."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Can you check the delivery status "
                        "of my order ORD-1001?"
                    ),
                },
            ]
        }
    )

    # 7. Print final response
    print("\nFinal Agent Response:")
    print(result["messages"][-1].content)

    # Show whether the LLM called the tool
    print("\nTool calls made:")
    for message in result["messages"]:
        if getattr(message, "tool_calls", None):
            print(message.tool_calls)


if __name__ == "__main__":
    asyncio.run(main())

# poetry run python mcp_agent.py
