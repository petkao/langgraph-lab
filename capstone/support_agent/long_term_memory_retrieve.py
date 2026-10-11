
import sqlite3

# Connect to the existing database
conn = sqlite3.connect("customer_messages.db")

# Retrieve messages without inserting anything
cursor = conn.execute("""
SELECT message_id, role, text
FROM messages
WHERE customer_id = ?
ORDER BY message_id DESC 
LIMIT 2
""", ("customer-1001",))

print("Messages retrieved from persistent storage:")
print("Latest 2 customer messages:")

for row in cursor.fetchall():
    print(row)

# Retrieve an older message by its ID
cursor = conn.execute("""
SELECT message_id, role, text
FROM messages
WHERE customer_id = ?
AND message_id = ?
""", ("customer-1001", "msg-001"))

print("\nHistorical message:")

result = cursor.fetchone()
print(result)

conn.close()

# poetry run python long_term_memory_retrieve.py
