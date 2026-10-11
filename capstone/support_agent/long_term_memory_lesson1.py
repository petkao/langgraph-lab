from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

namespace = ("customers", "customer-1001", "messages")

# Store three messages
store.put(namespace, "msg-001", {
    "text": "I purchased a laptop.",
    "role": "human"
})

store.put(namespace, "msg-002", {
    "text": "My laptop will not turn on.",
    "role": "human"
})

store.put(namespace, "msg-003", {
    "text": "I want a replacement.",
    "role": "human"
})

# Retrieve all three messages
results = store.search(namespace, limit=10)

print("Retrieved messages:")

for item in results:
    print(item.key, item.value)

# Retrieve one specific message
result = store.get(namespace, "msg-002")

print("\nSpecific message:")
print(result.value)

# poetry run python long_term_memory_lesson1.py