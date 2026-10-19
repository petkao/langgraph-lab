from hitl_graph_postgres import graph

config = {
    "configurable": {
        "thread_id": "postgres-test-001"
    }
}

history = list(graph.get_state_history(config))

print("Number of checkpoints:", len(history))

for i, snapshot in enumerate(history):
    print(f"\nCheckpoint {i + 1}")
    print("State:", snapshot.values)
    print("Next:", snapshot.next)
    print("Created:", snapshot.created_at)

# poetry run python inspect_postgres_history.py
