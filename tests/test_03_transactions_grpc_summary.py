from conftest import GATEWAY_URL, assert_status, clear_gateway_rate_limit_keys, create_transaction, get_user_transactions


def test_transaction_creation_and_grpc_summary(http, registered_user):
    user_id = registered_user["id"]

    create_transaction(http, user_id, 1000, "Salary", "income", "Pytest salary")
    create_transaction(http, user_id, 250, "Groceries", "expense", "Pytest groceries")
    create_transaction(http, user_id, 150, "Transport", "expense", "Pytest transport")

    transactions = get_user_transactions(http, user_id)
    assert len(transactions) >= 3

    clear_gateway_rate_limit_keys()
    summary_response = http.get(
        f"{GATEWAY_URL}/transactions/{user_id}/summary",
        timeout=20,
    )
    assert_status(summary_response, 200)
    summary = summary_response.json()

    assert summary["user_id"] == user_id
    assert summary["transport"] == "grpc"
    assert summary["total_income"] >= 1000
    assert summary["total_expense"] >= 400
    assert summary["balance"] >= 600


def test_transaction_create_is_idempotent_when_id_is_reused(http, registered_user):
    user_id = registered_user["id"]
    transaction_id = f"pytest-idempotent-{user_id}"

    first = create_transaction(
        http,
        user_id=user_id,
        amount=123,
        category="Idempotency",
        tx_type="expense",
        description="First call",
        tx_id=transaction_id,
    )
    second = create_transaction(
        http,
        user_id=user_id,
        amount=123,
        category="Idempotency",
        tx_type="expense",
        description="Second retry",
        tx_id=transaction_id,
    )

    assert first["id"] == transaction_id
    assert second["id"] == transaction_id

    transactions = get_user_transactions(http, user_id)
    matching = [tx for tx in transactions if tx["id"] == transaction_id]
    assert len(matching) == 1
