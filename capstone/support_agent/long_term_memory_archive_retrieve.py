
import sqlite3

# Open the archive database
conn = sqlite3.connect("pruning_archive.db")

# Retrieve archived messages
cursor = conn.execute("""
    SELECT message_id, role, content
    FROM archived_messages
    ORDER BY message_id
""")

print("Messages retrieved from SQLite archive:")

for row in cursor.fetchall():
    print(row)

conn.close()

# poetry run python long_term_memory_archive_retrieve.py