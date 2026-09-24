from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager

from lessons.lesson18_capstone import parent_graph, pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    pool.wait()
    yield
    pool.close()


app = FastAPI(lifespan=lifespan)


class CustomerRequest(BaseModel):
    actor_id: str
    customer_message: str
    order_id: str = ""
    refund_id: str = ""
    refund_amount: float = 0.0


@app.post("/customer-service")
def customer_service(request: CustomerRequest):

    result = parent_graph.invoke({
        "actor_id": request.actor_id,
        "customer_message": request.customer_message,
        "messages": [],
        "intent": "",
        "order_id": request.order_id,
        "refund_id": request.refund_id,
        "refund_amount": request.refund_amount,
        "response": "",
    })

    return {
        "intent": result["intent"],
        "response": result["response"],
    }