from hitl_graph_postgres import graph

config = {
    "configurable": {
        "thread_id": "postgres-test-001"
    }
}

result = graph.invoke(
    {
        "request": "Replace laptop ORD-1001",
        "approved": None,
        "status": "pending"
    },
    config=config
)

print("\nGraph result:")
print(result)

snapshot = graph.get_state(config)

print("\nSaved state:")
print(snapshot.values)

print("\nNext node:")
print(snapshot.next)

# poetry run python test_postgres_checkpoint.py
