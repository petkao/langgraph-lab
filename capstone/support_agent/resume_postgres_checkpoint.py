from langgraph.types import Command
from hitl_graph_postgres import graph

config = {
    "configurable": {
        "thread_id": "postgres-test-001"
    }
}

print("State before resuming:")
snapshot = graph.get_state(config)
print(snapshot.values)
print("Next:", snapshot.next)

print("\nResuming with human approval...")

result = graph.invoke(
    Command(resume="yes"),
    config=config
)

print("\nFinal result:")
print(result)

print("\nState after resuming:")
snapshot = graph.get_state(config)
print(snapshot.values)
print("Next:", snapshot.next)

# poetry run python resume_postgres_checkpoint.py
