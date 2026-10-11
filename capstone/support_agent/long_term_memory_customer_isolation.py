
import sqlite3

DB_PATH = "customer_isolation.db"

with sqlite3.connect(DB_PATH) as conn:

    conn.execute("""
        CREATE TABLE IF NOT EXISTS customer_messages (
            customer_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            content TEXT NOT NULL,
            PRIMARY KEY (customer_id, message_id)
        )
    """)

    sample_messages = [
        (
            "customer-1001",
            "msg-102",
            "The laptop stopped turning on yesterday."
        ),
        (
            "customer-1001",
            "msg-106",
            "My Dell laptop battery was replaced two weeks ago."
        ),
        (
            "customer-2002",
            "msg-201",
            "My printer stopped working."
        )
    ]

    conn.executemany("""
        INSERT OR IGNORE INTO customer_messages
        (customer_id, message_id, content)
        VALUES (?, ?, ?)
    """, sample_messages)

    conn.commit()

    customer_id = "customer-1001"

    records = conn.execute("""
        SELECT message_id, content
        FROM customer_messages
        WHERE customer_id = ?
    """, (customer_id,)).fetchall()

print(f"\nMessages belonging to {customer_id}:")

for message_id, content in records:
    print(message_id, "-", content)


import json

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

with sqlite3.connect(DB_PATH) as conn:

    # Create customer-specific embedding table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customer_embeddings (
            customer_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            embedding TEXT NOT NULL,
            PRIMARY KEY (customer_id, message_id)
        )
    """)

    # Read messages from all customers for indexing
    messages = conn.execute("""
        SELECT customer_id, message_id, content
        FROM customer_messages
    """).fetchall()

    for customer_id, message_id, content in messages:

        # Check whether embedding already exists
        existing = conn.execute("""
            SELECT 1
            FROM customer_embeddings
            WHERE customer_id = ?
              AND message_id = ?
        """, (customer_id, message_id)).fetchone()

        if existing:
            print(
                f"Already indexed: {customer_id} / {message_id}"
            )
            continue

        # Generate embedding for new message
        vector = embeddings.embed_query(content)

        conn.execute("""
            INSERT INTO customer_embeddings
            (customer_id, message_id, embedding)
            VALUES (?, ?, ?)
        """, (
            customer_id,
            message_id,
            json.dumps(vector)
        ))

        print(
            f"Indexed: {customer_id} / {message_id}"
        )

    conn.commit()


import math


def cosine_similarity(a, b):
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(y * y for y in b))

    return dot_product / (magnitude_a * magnitude_b)


# In production, this ID must come from authenticated context.
search_customer_id = "customer-2002"

# question = "Why wasn't my computer working?"
question = "What problem did I report with my printer?"

# Generate embedding for the customer's question
question_vector = embeddings.embed_query(question)

# Retrieve ONLY this customer's stored embeddings
with sqlite3.connect(DB_PATH) as conn:
    records = conn.execute("""
        SELECT
            e.message_id,
            m.content,
            e.embedding
        FROM customer_embeddings AS e
        JOIN customer_messages AS m
          ON e.customer_id = m.customer_id
         AND e.message_id = m.message_id
        WHERE e.customer_id = ?
    """, (search_customer_id,)).fetchall()

results = []

for message_id, content, embedding_json in records:
    vector = json.loads(embedding_json)

    score = cosine_similarity(question_vector, vector)

    results.append({
        "message_id": message_id,
        "content": content,
        "score": score
    })

results.sort(
    key=lambda item: item["score"],
    reverse=True
)

print(f"\nSemantic search for {search_customer_id}:")
print("Question:", question)

for match in results[:2]:
    print(
        match["message_id"],
        f"Score: {match['score']:.4f}",
        match["content"]
    )

with sqlite3.connect("customer_isolation.db") as conn:
    conn.execute("""
        INSERT OR IGNORE INTO customer_messages
        (customer_id, message_id, content)
        VALUES (?, ?, ?)
    """, (
        "customer-1001",
        "msg-202",
        "My laptop has a keyboard problem."
    ))

    conn.commit()

    records = conn.execute("""
        SELECT customer_id, message_id, content
        FROM customer_messages
        WHERE message_id = ?
        ORDER BY customer_id
    """, ("msg-202",)).fetchall()

print("\nMessages sharing the same message ID:")
for record in records:
    print(record)
    
# poetry run python long_term_memory_customer_isolation.py
