
import uuid
import streamlit as st

from langgraph.types import Command
from hitl_graph import graph


st.title("LangGraph Human-in-the-Loop")

# 1. Create a thread ID for this Streamlit session
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# 2. Track whether the workflow has started
if "started" not in st.session_state:
    st.session_state.started = False

# 3. Configure LangGraph
config = {
    "configurable": {
        "thread_id": st.session_state.thread_id
    }
}

st.write("Thread ID:", st.session_state.thread_id)

# 4. Start workflow
if not st.session_state.started:
    if st.button("Request Laptop Replacement"):
        graph.invoke(
            {
                "request": "Replace laptop ORD-1001",
                "approved": None,
                "status": "pending"
            },
            config=config
        )

        st.session_state.started = True
        st.rerun()

# 5. Retrieve graph state
if st.session_state.started:
    snapshot = graph.get_state(config)

    st.write("Request:", snapshot.values["request"])
    st.write("Status:", snapshot.values["status"])

    # 6. Human approval
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

    # 7. Display final status
    elif snapshot.values["status"] == "approved":
        st.success("Replacement approved!")

    elif snapshot.values["status"] == "rejected":
        st.error("Replacement rejected!")
        
# poetry run streamlit run hitl_streamlit.py