from typing import TypedDict


class RefundState(TypedDict):
    amount: float
    status: str


def evaluate_refund(state: RefundState):

    if state["amount"] <= 500:
        return {
            "status": "automatic"
        }

    return {
        "status": "human_approval"
    }

def test_small_refund():

    state = {
        "amount": 200,
        "status": ""
    }

    result = evaluate_refund(state)

    assert result["status"] == "automatic"


def test_large_refund():

    state = {
        "amount": 1200,
        "status": ""
    }

    result = evaluate_refund(state)

    assert result["status"] == "human_approval"

test_small_refund()
test_large_refund()

print("All tests passed.")

# poetry run python -m lessons.lesson16_testing