from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from typing import TypedDict
from langgraph.graph.message import add_messages
from typing import Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState
from langchain_core.messages import HumanMessage, RemoveMessage
from langgraph.checkpoint.memory import InMemorySaver
import sqlite3
import json
import math
from langchain_openai import OpenAIEmbeddings

from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    customer_id: str
    retrieved_messages: list[str]

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0
)

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)


def archive_messages(customer_id: str, messages):
    with sqlite3.connect("customer_isolation.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customer_messages (
                customer_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                content TEXT NOT NULL,
                PRIMARY KEY (customer_id, message_id)
            )
        """)

        conn.executemany("""
            INSERT OR IGNORE INTO customer_messages
            (customer_id, message_id, content)
            VALUES (?, ?, ?)
        """, [
            (customer_id, msg.id, msg.content)
            for msg in messages
        ])

        conn.commit()

    print(
        f"\nArchived {len(messages)} messages "
        f"for customer {customer_id}."
    )


def cosine_similarity(a, b):
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(y * y for y in b))

    return dot_product / (magnitude_a * magnitude_b)



def index_archived_messages(state: AgentState):
    customer_id = state["customer_id"]

    new_count = 0

    with sqlite3.connect("customer_isolation.db") as conn:

        # Find this customer's messages without embeddings
        records = conn.execute("""
            SELECT m.message_id, m.content
            FROM customer_messages AS m
            LEFT JOIN customer_embeddings AS e
              ON m.customer_id = e.customer_id
             AND m.message_id = e.message_id
            WHERE m.customer_id = ?
              AND e.message_id IS NULL
        """, (customer_id,)).fetchall()

        for message_id, content in records:

            # Generate embedding
            vector = embeddings.embed_query(content)

            # Store embedding with customer identity
            conn.execute("""
                INSERT OR IGNORE INTO customer_embeddings
                (customer_id, message_id, embedding)
                VALUES (?, ?, ?)
            """, (
                customer_id,
                message_id,
                json.dumps(vector)
            ))

            new_count += 1

        conn.commit()

    print(
        f"\nNew messages indexed for {customer_id}: "
        f"{new_count}"
    )

    return {}



def retrieve_archived_messages(state: AgentState):
    customer_id = state["customer_id"]

    # Use the latest message from the active conversation
    search_term = state["messages"][-1].content

    # Generate embedding for the current question
    query_vector = embeddings.embed_query(search_term)

    # Read ONLY the specified customer's embeddings
    with sqlite3.connect("customer_isolation.db") as conn:
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
        """, (customer_id,)).fetchall()

    results = []

    for message_id, content, embedding_json in records:
        message_vector = json.loads(embedding_json)

        score = cosine_similarity(
            query_vector,
            message_vector
        )

        results.append({
            "message_id": message_id,
            "content": content,
            "score": score
        })

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    top_matches = results[:2]

    print(
        f"\nSemantic retrieval for customer {customer_id}:"
    )

    for match in top_matches:
        print(
            match["message_id"],
            f"Score: {match['score']:.4f}",
            match["content"]
        )

    return {
        "retrieved_messages": [
            match["content"] for match in top_matches
        ]
    }


    # Rank by similarity
    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    # Select top two matches
    top_matches = results[:2]

    print("\nSemantically retrieved historical messages:")

    for match in top_matches:
        print(
            match["message_id"],
            f"Score: {match['score']:.4f}",
            match["content"]
        )

    return {
        "retrieved_messages": [
            match["content"] for match in top_matches
        ]
    }



def generate_answer(state: AgentState):

    recent_messages = state["messages"]
    retrieved_messages = state["retrieved_messages"]

    historical_context = "\n".join(retrieved_messages)

    system_message = SystemMessage(
        content=(
            "You are a customer support assistant.\n"
            "Answer the customer's question using the "
            "conversation history provided.\n"
            "Do not invent information.\n\n"
            "Relevant historical messages:\n"
            f"{historical_context}"
        )
    )

    response = llm.invoke(
        [system_message] + recent_messages
    )

    print("\nLLM-generated answer:")
    print(response.content)

    return {}


# Node that removes older messages

def prune_messages(state: AgentState):

    print("\nDEBUG - State received by pruning node:")
    print(state)

    messages = state["messages"]

    print("\nMessages BEFORE pruning:")
    for msg in messages:
        print(msg.id, msg.content)

    # Keep the latest 2 messages
    messages_to_remove = messages[:-2]

    # Step 1: Archive older messages in SQLite
    if messages_to_remove:
        archive_messages(
            state["customer_id"],
            messages_to_remove
        )

    # Step 2: Remove them from active LangGraph state
    return {
        "messages": [
            RemoveMessage(id=msg.id)
            for msg in messages_to_remove
        ]
    }



# Build LangGraph
# builder = StateGraph(MessagesState)
builder = StateGraph(AgentState)

builder.add_node("prune_messages", prune_messages)
builder.add_node("retrieve_archived_messages", retrieve_archived_messages)
builder.add_node("generate_answer", generate_answer)
builder.add_node("index_archived_messages", index_archived_messages)

builder.add_edge(START, "prune_messages")

builder.add_edge(
    "prune_messages",
    "index_archived_messages"
)

builder.add_edge(
    "index_archived_messages",
    "retrieve_archived_messages"
)

builder.add_edge(
    "retrieve_archived_messages",
    "generate_answer"
)

builder.add_edge("generate_answer", END)

graph = builder.compile(checkpointer=InMemorySaver())


# Create five messages
'''
initial_messages = [
    HumanMessage(content=f"Customer message {i}", id=f"msg-{i}")
    for i in range(1, 6)
]
'''

'''
initial_messages = [
    HumanMessage(
        content="My Dell laptop battery was replaced two weeks ago.",
        id="msg-106"
    ),
    HumanMessage(
        content="I purchased a Dell laptop last month.",
        id="msg-101"
    ),
    HumanMessage(
        content="The laptop stopped turning on yesterday.",
        id="msg-102"
    ),
    HumanMessage(
        content="My order number is ORD-1001.",
        id="msg-103"
    ),
    HumanMessage(
        content="I contacted customer support.",
        id="msg-104"
    ),
    HumanMessage(
        content="What was the problem I reported with my laptop?",
        id="msg-105"
    )
]
'''

initial_messages = [
    HumanMessage(
        content="I bought a printer recently.",
        id="msg-202"
    ),
    HumanMessage(
        content="I contacted customer support about my printer.",
        id="msg-203"
    ),
    HumanMessage(
        content="What problem did I report with my printer?",
        id="msg-204"
    )
]

'''
config = {
    "configurable": {
        "thread_id": "pruning-lesson-001"
    }
}
'''

config = {
    "configurable": {
        "thread_id": "customer-2002-lesson"
    }
}

# Execute graph
'''
result = graph.invoke(
    {"messages": initial_messages},
    config=config
)
'''

result = graph.invoke(
    {
        "messages": initial_messages,
        # "customer_id": "customer-1001",
        # "search_term": "Why wasn't my computer working?"
        "customer_id": "customer-2002"
    },
    config=config
)

print("\nRetrieved messages in LangGraph state:")
print(result["retrieved_messages"])

print("\nMessages AFTER pruning:")

for msg in result["messages"]:
    print(msg.id, msg.content)

# Inspect saved checkpoint
snapshot = graph.get_state(config)

print("\nMessages in checkpoint:")
for msg in snapshot.values["messages"]:
    print(msg.id, msg.content)

# poetry run python long_term_memory_pruning.py

