
import sqlite3
import json
import math

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)


def cosine_similarity(a, b):
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(y * y for y in b))

    return dot_product / (magnitude_a * magnitude_b)


# New customer question
question = "Why wasn't my computer working?"

# Generate embedding ONLY for the question
question_vector = embeddings.embed_query(question)

# Read previously stored embeddings
with sqlite3.connect("customer_embeddings.db") as conn:
    records = conn.execute("""
        SELECT message_id, content, embedding
        FROM message_embeddings
    """).fetchall()

results = []

for message_id, content, embedding_json in records:

    # Convert stored JSON back into a Python list
    message_vector = json.loads(embedding_json)

    score = cosine_similarity(
        question_vector,
        message_vector
    )

    results.append({
        "message_id": message_id,
        "content": content,
        "score": score
    })

# Rank by semantic similarity
results.sort(
    key=lambda item: item["score"],
    reverse=True
)

# Retrieve Top 2
top_matches = results[:2]

print("\nCustomer question:")
print(question)

print("\nTop 2 matching historical messages:")

for match in top_matches:
    print(
        match["message_id"],
        f"Score: {match['score']:.4f}",
        match["content"]
    )


# poetry run python long_term_memory_vector_search.py