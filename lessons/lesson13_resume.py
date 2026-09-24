from langgraph.types import Command

from lessons.lesson13_approval import graph, pool


config = {
    "configurable": {
        "thread_id": "lesson13-refund-001"
    }
}

print("Opening PostgreSQL pool...")

pool.open()
pool.wait()

print("Resuming workflow...")

result = graph.invoke(
    Command(resume="approved"),
    config=config,
)

print("\nRESUMED FROM POSTGRESQL:")
print(result)

pool.close()