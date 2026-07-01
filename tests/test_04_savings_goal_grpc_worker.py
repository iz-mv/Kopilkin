from conftest import (
    GATEWAY_URL,
    SAVINGS_URL,
    TINY_PNG_BYTES,
    assert_status,
    clear_gateway_rate_limit_keys,
    create_goal,
    get_goal_by_id,
    get_goal_operation,
    get_user_transactions,
    wait_for,
)


def test_goal_image_upload_uses_minio(http, registered_user):
    user_id = registered_user["id"]
    goal = create_goal(http, user_id, title="Pytest Image Goal", target_amount=2000)

    response = http.post(
        f"{SAVINGS_URL}/goals/{goal['id']}/image",
        files={"file": ("goal.png", TINY_PNG_BYTES, "image/png")},
        timeout=30,
    )
    assert_status(response, 200)
    updated_goal = response.json()

    assert updated_goal["id"] == goal["id"]
    assert updated_goal["image_url"]
    assert "kopilkin-files" in updated_goal["image_url"]
    assert "goals" in updated_goal["image_url"]


def test_create_goal_operation_via_grpc_then_worker_confirms_and_creates_transaction(http, registered_user):
    clear_gateway_rate_limit_keys()
    user_id = registered_user["id"]
    goal = create_goal(http, user_id, title="Pytest gRPC Goal", target_amount=1500)

    operation_response = http.post(
        f"{GATEWAY_URL}/grpc/goals/{goal['id']}/operations",
        json={"user_id": user_id, "operation_type": "DEPOSIT", "amount": 500},
        timeout=20,
    )
    assert_status(operation_response, 200)
    operation = operation_response.json()

    assert operation["transport"] == "grpc"
    assert operation["operation_type"] == "DEPOSIT"
    assert operation["status"] == "PENDING"
    assert operation["goal_id"] == goal["id"]

    confirmed_operation = wait_for(
        lambda: (
            op if (op := get_goal_operation(http, goal["id"], operation["id"])) and op["status"] == "CONFIRMED" else None
        ),
        timeout_seconds=60,
        interval_seconds=1,
        description="worker to confirm DEPOSIT operation",
    )
    assert confirmed_operation["failure_reason"] in (None, "")

    updated_goal = wait_for(
        lambda: (
            g if (g := get_goal_by_id(http, user_id, goal["id"])) and g["current_amount"] >= 500 else None
        ),
        timeout_seconds=30,
        interval_seconds=1,
        description="goal current amount to be updated",
    )
    assert updated_goal["current_amount"] >= 500

    expected_transaction_id = f"tx-goal-operation-{operation['id']}"
    transaction = wait_for(
        lambda: next(
            (tx for tx in get_user_transactions(http, user_id) if tx["id"] == expected_transaction_id),
            None,
        ),
        timeout_seconds=30,
        interval_seconds=1,
        description="linked transaction from worker",
    )
    assert transaction["type"] == "expense"
    assert transaction["category"] == "Savings Goal"
    assert transaction["amount"] == 500
    assert "Saved for goal" in (transaction["description"] or "")


def test_worker_marks_withdraw_as_failed_when_amount_is_too_high(http, registered_user):
    clear_gateway_rate_limit_keys()
    user_id = registered_user["id"]
    goal = create_goal(http, user_id, title="Pytest Failed Withdraw Goal", target_amount=1000)

    operation_response = http.post(
        f"{GATEWAY_URL}/grpc/goals/{goal['id']}/operations",
        json={"user_id": user_id, "operation_type": "WITHDRAW", "amount": 9999},
        timeout=20,
    )
    assert_status(operation_response, 200)
    operation = operation_response.json()

    failed_operation = wait_for(
        lambda: (
            op if (op := get_goal_operation(http, goal["id"], operation["id"])) and op["status"] == "FAILED" else None
        ),
        timeout_seconds=60,
        interval_seconds=1,
        description="worker to fail excessive WITHDRAW operation",
    )
    assert "Not enough" in (failed_operation["failure_reason"] or "")

    updated_goal = get_goal_by_id(http, user_id, goal["id"])
    assert updated_goal is not None
    assert updated_goal["current_amount"] == 0

    expected_transaction_id = f"tx-goal-operation-{operation['id']}"
    transactions = get_user_transactions(http, user_id)
    assert not any(tx["id"] == expected_transaction_id for tx in transactions)
