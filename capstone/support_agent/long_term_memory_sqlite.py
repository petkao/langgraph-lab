
import sqlite3

# Connect to persistent SQLite database
conn = sqlite3.connect("customer_messages.db")

# Create a table if it doesn't already exist
conn.execute("""
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    customer_id TEXT,
    role TEXT,
    text TEXT
)
""")

# Store three messages
messages = [
    ("msg-001", "customer-1001", "human", "I purchased a laptop."),
    ("msg-002", "customer-1001", "human", "My laptop will not turn on."),
    ("msg-003", "customer-1001", "human", "I want a replacement.")
]

conn.executemany("""
INSERT OR IGNORE INTO messages
(message_id, customer_id, role, text)
VALUES (?, ?, ?, ?)
""", messages)

conn.commit()

# Retrieve all messages for the customer
cursor = conn.execute("""
SELECT message_id, role, text
FROM messages
WHERE customer_id = ?
ORDER BY message_id
""", ("customer-1001",))

print("Persistent customer messages:")

for row in cursor.fetchall():
    print(row)

conn.close()

# poetry run python long_term_memory_sqlite.py
