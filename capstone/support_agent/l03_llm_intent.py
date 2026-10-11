from dotenv import load_dotenv
from typing import TypedDict, Literal

from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

class IntentClassification(BaseModel):
    intent: Literal[
        "replacement",
        "refund",
        "general_support"
    ]   

load_dotenv()

model = ChatOpenAI(
    model = "gpt-5-mini",
    temperature=0
)

intent_model = model.with_structured_output(IntentClassification)

class SupportState(TypedDict):
    customer_message: str
    intent: str
    status: str
    response: str

def receive_request(state: SupportState):
    print(f"Customer: {state["customer_message"]}")

    return {
        "status": "request_received"
    }

def understand_request(state: SupportState):
   classification = intent_model.invoke(
    [
        (
            "system",
            """
            You are an intent classification agent for a customer support system.

            Your role is to analyze the customer's message and determine
            which support workflow should handle the request.

            You do not answer the customer's question.
            You do not perform refunds or replacements.
            You only classify the customer's primary intent.

            Classify the request into exactly one of these intents:

            - replacement: the customer wants an item replaced
            - refund: the customer wants their money returned
            - general_support: any other support request

            Choose the intent based on the meaning of the customer's request,
            not just specific keywords.            """,
        ),
        ("human",state["customer_message"])
    ]
   )
   return {
    "intent": classification.intent,
    "status": "request_understood",
   }

def replacement_agent(state: SupportState):
    return {
        "response": "Let me check whether this order is eligible for replacement.",
        "status": "replacement_agent"
    }

def refund_agent(state: SupportState):
    return {
        "response": "Let me check whether this order is eligible for a refund.",
        "status": "refund_agent"
    }

def general_support_agent(state: SupportState):
    return {
        "response": "Let me help you with your support question.",
        "status": "general_support_agent"
    }

def route_by_intent(state: SupportState):
    return state["intent"]



builder = StateGraph(SupportState)

builder.add_node("receive_request", receive_request)
builder.add_node("understand_request", understand_request)
builder.add_node("general_support_agent", general_support_agent)
builder.add_node("replacement_agent",replacement_agent)
builder.add_node("refund_agent", refund_agent)


builder.add_edge(START, "receive_request")
builder.add_edge("receive_request", "understand_request")
builder.add_conditional_edges(
    "understand_request",
    route_by_intent,
    {
        "replacement": "replacement_agent",
        "refund": "refund_agent",
        "general_support": "general_support_agent",
    }
)

builder.add_edge("replacement_agent", END)
builder.add_edge("refund_agent", END)
builder.add_edge("general_support_agent", END)


graph = builder.compile()


initial_state = {
    # "customer_message": "My laptop arrived damaged. Can I get a replacement?",
    # "customer_message": "I want a refund for my laptop.",
    # "customer_message": "How do I reset my laptop password?",
    "customer_message": "The computer I received yesterday won't turn on. Please send me another one.",
    "intent": "",
    "status": "", 
    "response": "",
}

result = graph.invoke(initial_state)

print("\nFinal State:")
print(result)

# poetry run python l03_llm_intent.py






