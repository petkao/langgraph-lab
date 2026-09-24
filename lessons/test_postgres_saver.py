from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://tzechungkao@localhost:5432/langgraph_lab"

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()

    print("PostgresSaver setup complete.")