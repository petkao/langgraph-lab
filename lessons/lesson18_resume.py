from langgraph.types import Command

from lessons.lesson18_capstone import (
    refund_graph,
    pool,
)


config = {
    "configurable": {
        "thread_id": "lesson18-refund-002"
    }
}


if __name__ == "__main__":

    pool.open()
    pool.wait()

    result = refund_graph.invoke(
        Command(resume="approved"),
        config=config,
    )

    print(result)

    pool.close()

# poetry run python -m lessons.lesson18_resume