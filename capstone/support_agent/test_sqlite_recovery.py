import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect("customer_memory.db")
memory = SqliteSaver(conn)

config = {
    "configurable": {
        "thread_id": "customer-002"
    }
}

checkpoint = memory.get_tuple(config)

if checkpoint:
    state = checkpoint.checkpoint["channel_values"]

    print("Recovered Order:", state["order_id"])
    print("Recovered Stage:", state["workflow_stage"])
    print("Recovered Messages:", len(state["messages"]))
else:
    print("No checkpoint found")

conn.close()