
import streamlit as st
from langgraph.types import Command
from hitl_graph_sqlite import graph


st.title("Persistent HITL with SQLite")

# Fixed thread ID for this lesson
THREAD_ID = "hitl-sqlite-001"

config = {
    "configurable": {
        "thread_id": THREAD_ID
    }
}

st.write("Thread ID:", THREAD_ID)

# Retrieve existing checkpoint
snapshot = graph.get_state(config)

# Start a new workflow only if no checkpoint exists
if not snapshot.values:
    if st.button("Request Laptop Replacement"):
        graph.invoke(
            {
                "request": "Replace laptop ORD-1001",
                "approved": None,
                "status": "pending"
            },
            config=config
        )
        st.rerun()

else:
    st.write("Request:", snapshot.values["request"])
    st.write("Status:", snapshot.values["status"])

    if snapshot.interrupts:
        st.warning("Human approval required")

        if st.button("Approve"):
            graph.invoke(
                Command(resume="yes"),
                config=config
            )
            st.rerun()

        if st.button("Reject"):
            graph.invoke(
                Command(resume="no"),
                config=config
            )
            st.rerun()

    elif snapshot.values["status"] == "approved":
        st.success("Replacement approved!")

    elif snapshot.values["status"] == "rejected":
        st.error("Replacement rejected!")
