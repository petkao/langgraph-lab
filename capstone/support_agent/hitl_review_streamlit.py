
import uuid
import streamlit as st

from langgraph.types import Command
from hitl_review_graph import graph


st.title("HITL — Human Review")

# Use a new thread for each review session
if "review_thread_id" not in st.session_state:
    st.session_state.review_thread_id = str(uuid.uuid4())

config = {
    "configurable": {
        "thread_id": st.session_state.review_thread_id
    }
}

st.caption(f"Thread ID: {st.session_state.review_thread_id}")

snapshot = graph.get_state(config)


# Start a new review
if not snapshot.values:
    if st.button("Create Replacement Proposal"):
        graph.invoke(
            {
                "order_id": "ORD-1001",
                "proposed_quantity": 2,
                "approved_quantity": None,
                "status": "pending"
            },
            config=config
        )
        st.rerun()


# Display existing review
else:
    state = snapshot.values

    st.write("Order:", state["order_id"])
    st.write("Proposed Quantity:", state["proposed_quantity"])
    st.write("Status:", state["status"])

    if snapshot.interrupts:
        st.warning("Human review required")

        action = st.radio(
            "Choose an action",
            ["approve", "modify", "reject"]
        )

        quantity = state["proposed_quantity"]

        if action == "modify":
            quantity = st.number_input(
                "Corrected quantity",
                min_value=1,
                value=state["proposed_quantity"],
                step=1
            )

        if st.button("Submit Review"):
            response = {
                "action": action,
                "quantity": int(quantity)
            }

            graph.invoke(
                Command(resume=response),
                config=config
            )

            st.rerun()

    elif state["status"] == "approved":
        st.success("Replacement approved!")
        st.write(
            "Approved Quantity:",
            state["approved_quantity"]
        )

    elif state["status"] == "rejected":
        st.error("Replacement rejected!")

    if state["status"] in ("approved", "rejected"):
        if st.button("Start New Review"):
            st.session_state.review_thread_id = str(uuid.uuid4())
            st.rerun()

# from hitl_review_graph import graph

# Replace this with the Thread ID shown in Streamlit.
config = {
    "configurable": {
        "thread_id": "YOUR-THREAD-ID"
    }
}

snapshot = graph.get_state(config)

print(snapshot.values)
print("Next:", snapshot.next)
print("Interrupts:", snapshot.interrupts)

#
'''
from hitl_review_graph import graph

# Replace this with the Thread ID shown in Streamlit.
config = {
    "configurable": {
        "thread_id": "YOUR-THREAD-ID"
    }
}

snapshot = graph.get_state(config)

print(snapshot.values)
print("Next:", snapshot.next)
print("Interrupts:", snapshot.interrupts)

'''
from hitl_review_graph import graph

# Replace this with the Thread ID shown in Streamlit.
config = {
    "configurable": {
        "thread_id": "181e26ed-6fbb-450d-9d16-0aa764c2e95a"
    }
}

snapshot = graph.get_state(config)

print(snapshot.values)
print("Next:", snapshot.next)
print("Interrupts:", snapshot.interrupts)

'''
