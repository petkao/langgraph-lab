import streamlit as st
import re

from langchain_core.messages import HumanMessage
from l08_persistent_memory import graph

import uuid

def extract_order_id(message: str) -> str | None:
    match = re.search(r"\bORD-\d+\b", message, re.IGNORECASE)
    return match.group(0).upper() if match else None

st.set_page_config(
    page_title="Customer Support Chatbot",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Customer Support Chatbot")
st.caption("Powered by LangGraph and OpenAI")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Assign a unique LangGraph thread ID to this browser session
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

st.caption(f"Conversation ID: {st.session_state.thread_id}")

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Accept customer input
if prompt := st.chat_input("How can I help you today?"):

    # Display customer message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.write(prompt)

    # Retrieve the order ID from the customer's message
    order_id = extract_order_id(prompt)

    # Configure LangGraph conversation memory
    config = {
        "configurable": {
            "thread_id": st.session_state.thread_id
        }
    }

    # Prepare the customer message for LangGraph
    graph_input = {
        "messages": [HumanMessage(content=prompt)],
        "customer_message": prompt,
    }

    # Include the order ID when the customer provides one
    if order_id:
        graph_input["order_id"] = order_id

    # Initialize a new conversation
    if len(st.session_state.messages) == 1:
        graph_input.update({
            "workflow_stage": "new_request",
            "intent": "",
            "status": "",
            "response": "",
            "replacement_eligible": None,
            "policy_reason": "",
            "order_data": {},
        })

    # Invoke the customer support agent
    with st.spinner("Checking your request..."):
        result = graph.invoke(graph_input, config=config)

    '''   
    print("\n=== LANGGRAPH RESULT ===")
    for key, value in result.items():
        print(f"{key}: {value}")
    '''

    # Retrieve the agent's response
    response = result.get("response") or (
        "I'm sorry, I couldn't process your request."
    )

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })

    with st.chat_message("assistant"):
        st.write(response)

# poetry run streamlit run app.py

'''
from l08_persistent_memory import graph

config = {
    "configurable": {
        "thread_id": "26acfeac-3de2-4a4e-bb87-2bcff21de8f5"
    }
}

snapshot = graph.get_state(config)

print("Order:", snapshot.values.get("order_id"))
print("Intent:", snapshot.values.get("intent"))
print("Workflow Stage:", snapshot.values.get("workflow_stage"))
print("Status:", snapshot.values.get("status"))
print("Messages:", len(snapshot.values.get("messages", [])))



'''