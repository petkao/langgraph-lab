from lessons.customer_service_graph import customer_service_graph, pool

THREAD_ID = "696a4ebe-9da8-4c19-a7e3-31e5f051f896"

CHECKPOINT_ID = "1f1b634f-747c-6176-801e-05f3cce030fb"

config = {
    "configurable": {
        "thread_id": THREAD_ID,
        "checkpoint_id": CHECKPOINT_ID,
    }
}

pool.open()
pool.wait()

snapshot = customer_service_graph.get_state(config)

print("\n--- HISTORICAL CHECKPOINT ---")

print("Thread ID:")
print(snapshot.config["configurable"]["thread_id"])

print("Checkpoint ID:")
print(snapshot.config["configurable"]["checkpoint_id"])

print("\nCustomer message:")
print(snapshot.values.get("customer_message"))

print("\nIntent:")
print(snapshot.values.get("intent"))

print("\nNext:")
print(snapshot.next)

print("\nCreated:")
print(snapshot.created_at)

pool.close()

# poetry run python -m lessons.lesson11_get_checkpoint