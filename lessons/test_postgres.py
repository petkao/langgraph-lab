import psycopg

DB_URI = "postgresql://tzechungkao@localhost:5432/langgraph_lab"

with psycopg.connect(DB_URI) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user;")
        result = cur.fetchone()

        print("Database:", result[0])
        print("User:", result[1])