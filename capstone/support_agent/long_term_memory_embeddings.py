
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
import math
import sqlite3

load_dotenv()

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)


def cosine_similarity(a, b):
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(y * y for y in b))

    return dot_product / (magnitude_a * magnitude_b)

'''
# Historical customer messages
historical_messages = [
    "I purchased a Dell laptop last month.",
    "The laptop stopped turning on yesterday.",
    "My order number is ORD-1001.",
    "I would like to change my shipping address.",
    "The replacement computer arrived damaged."
]
'''

# Retrieve historical messages from SQLite
with sqlite3.connect("pruning_archive.db") as conn:
    cursor = conn.execute("""
        SELECT message_id, content
        FROM archived_messages
        ORDER BY message_id
    """)

    archived_records = cursor.fetchall()

historical_messages = [
    record[1] for record in archived_records
]

print("\nMessages loaded from SQLite:")

for message_id, content in archived_records:
    print(message_id, "-", content)



# Current customer question
question = "Why wasn't my computer working?"

# Generate embeddings
message_vectors = embeddings.embed_documents(
    historical_messages
)

question_vector = embeddings.embed_query(question)

# Calculate similarity for each historical message
results = []

for message, vector in zip(
    historical_messages, message_vectors
):
    score = cosine_similarity(question_vector, vector)
    results.append((score, message))

# Rank by similarity (highest first)
results.sort(reverse=True)

top_matches = results[:2]

print("\nTop 2 retrieved historical messages:")

for score, message in top_matches:
    print(f"{score:.4f} - {message}")

print("\nCustomer question:")
print(question)

print("\nHistorical messages ranked by similarity:")

for score, message in results:
    print(f"{score:.4f} - {message}")

# poetry run python long_term_memory_embeddings.py
