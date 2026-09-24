from lessons.customer_service_graph import customer_service_graph, pool

THREAD_ID = "696a4ebe-9da8-4c19-a7e3-31e5f051f896"

config = {
    "configurable": {
        "thread_id": THREAD_ID
    }
}

pool.open()
pool.wait()

history = customer_service_graph.get_state_history(config)

print("\n--- CHECKPOINT HISTORY ---")

for number, snapshot in enumerate(history, start=1):

    if number > 5:
        break

    checkpoint_id = snapshot.config["configurable"]["checkpoint_id"]

    print(f"\nCheckpoint {number}")

    print("Checkpoint ID:")
    print(checkpoint_id)

    print("Created:")
    print(snapshot.created_at)

    print("Intent:")
    print(snapshot.values.get("intent"))

    print("Customer message:")
    print(snapshot.values.get("customer_message"))

    print("Next:")
    print(snapshot.next)

pool.close()

# poetry run python -m lessons.lesson11_checkpoint_history