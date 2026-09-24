from lessons.customer_service_graph import customer_service_graph, pool

THREAD_ID = "696a4ebe-9da8-4c19-a7e3-31e5f051f896"

config = {
    "configurable": {
        "thread_id": THREAD_ID
    }
}

pool.open()
pool.wait()

snapshot = customer_service_graph.get_state(config)

print("\n--- CURRENT STATE ---")
# print(snapshot.values)

print("\n--- CURRENT STATE ---")

print("Customer message:")
print(snapshot.values.get("customer_message"))

print("\nIntent:")
print(snapshot.values.get("intent"))

print("\nResponse:")
print(snapshot.values.get("response"))

print("\nConversation:")
for message in snapshot.values.get("messages", []):
    print(
        f"{type(message).__name__}: "
        f"{message.content}"
    )

print("\nNext node:")
print(snapshot.next)

print("\nCreated at:")
print(snapshot.created_at)

pool.close()