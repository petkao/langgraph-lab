
import sqlite3
import json

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

# Step 1: Read historical messages
with sqlite3.connect("pruning_archive.db") as conn:
    records = conn.execute("""
        SELECT message_id, content
        FROM archived_messages
    """).fetchall()

# Step 2: Create persistent embedding storage
with sqlite3.connect("customer_embeddings.db") as conn:

    conn.execute("""
        CREATE TABLE IF NOT EXISTS message_embeddings (
            message_id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            embedding TEXT NOT NULL
        )
    """)

    # Step 3: Process historical messages
    for message_id, content in records:

        # Check whether embedding already exists
        existing = conn.execute("""
            SELECT 1
            FROM message_embeddings
            WHERE message_id = ?
        """, (message_id,)).fetchone()

        if existing:
            print(f"Already stored: {message_id}")
            continue

        # Generate embedding
        vector = embeddings.embed_query(content)

        # Store embedding and message ID
        conn.execute("""
            INSERT INTO message_embeddings
            (message_id, content, embedding)
            VALUES (?, ?, ?)
        """, (
            message_id,
            content,
            json.dumps(vector)
        ))

        print(f"Stored embedding: {message_id}")

    conn.commit()

    # Count stored embeddings
    count = conn.execute("""
        SELECT COUNT(*)
        FROM message_embeddings
    """).fetchone()[0]

print(f"\nTotal stored embeddings: {count}")

# poetry run python long_term_memory_embedding_store.py
