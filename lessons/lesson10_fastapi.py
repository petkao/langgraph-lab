from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uuid

from lessons.customer_service_graph import customer_service_graph, pool

@asynccontextmanager
async def lifespan(app: FastAPI):

    pool.open()
    pool.wait()

    yield

    pool.close()

app = FastAPI(lifespan=lifespan)


class CustomerRequest(BaseModel):
    customer_message: str
    thread_id: str | None = None


@app.post("/customer-service")
def customer_service(request: CustomerRequest):
    thread_id = request.thread_id or str(uuid.uuid4())

    config = {
    "configurable": {
        "thread_id": thread_id
    }
}

    result = customer_service_graph.invoke(
        {
            "customer_message": request.customer_message
        },
        config=config
    )

    return {
        "thread_id": thread_id,
        "intent": result["intent"],
        "response": result["response"]
    }