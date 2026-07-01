import os
import subprocess
import time
import uuid
from typing import Any, Callable

import pytest
import requests


GATEWAY_URL = os.getenv("KOPILKIN_GATEWAY_URL", "http://localhost:8088")
FRONTEND_URL = os.getenv("KOPILKIN_FRONTEND_URL", "http://localhost:5500")
AUTH_URL = os.getenv("KOPILKIN_AUTH_URL", "http://localhost:8001")
TRANSACTION_URL = os.getenv("KOPILKIN_TRANSACTION_URL", "http://localhost:8002")
SAVINGS_URL = os.getenv("KOPILKIN_SAVINGS_URL", "http://localhost:8003")
AGENT_URL = os.getenv("KOPILKIN_AGENT_URL", "http://localhost:8004")
RECSYS_URL = os.getenv("KOPILKIN_RECSYS_URL", "http://localhost:8005")
KAFKA_UI_URL = os.getenv("KOPILKIN_KAFKA_UI_URL", "http://localhost:8080")
MINIO_URL = os.getenv("KOPILKIN_MINIO_URL", "http://localhost:9000")


# 1x1 transparent PNG. Used to test MinIO upload endpoints without Pillow.
TINY_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def unique_email(prefix: str = "pytest") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


def assert_status(response: requests.Response, expected: int | tuple[int, ...]) -> None:
    if isinstance(expected, int):
        expected = (expected,)
    assert response.status_code in expected, (
        f"Expected status {expected}, got {response.status_code}. "
        f"Body: {response.text}"
    )


def wait_for(
    condition: Callable[[], Any],
    timeout_seconds: float = 45,
    interval_seconds: float = 1,
    description: str = "condition",
) -> Any:
    deadline = time.time() + timeout_seconds
    last_value = None

    while time.time() < deadline:
        last_value = condition()
        if last_value:
            return last_value
        time.sleep(interval_seconds)

    raise AssertionError(
        f"Timed out waiting for {description}. Last value: {last_value!r}"
    )


def clear_gateway_rate_limit_keys() -> None:
    """Best-effort cleanup for API Gateway Redis rate limiter.

    The gateway limits requests by client IP and minute. Re-running integration
    tests several times can hit HTTP 429. These tests are not meant to test the
    rate limiter, so we clear only rate_limit:* keys before the run.
    """
    try:
        scan = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "redis",
                "redis-cli",
                "--scan",
                "--pattern",
                "rate_limit:*",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        keys = [key.strip() for key in scan.stdout.splitlines() if key.strip()]
        if keys:
            subprocess.run(
                ["docker", "compose", "exec", "-T", "redis", "redis-cli", "DEL", *keys],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
    except Exception:
        # Tests should still be runnable even if Docker CLI is unavailable.
        pass


@pytest.fixture(scope="session", autouse=True)
def reset_rate_limiter_once() -> None:
    clear_gateway_rate_limit_keys()


@pytest.fixture(scope="session")
def http() -> requests.Session:
    session = requests.Session()
    # Do not force application/json globally: Kafka UI is an HTML/Spring app and
    # may return 406 for the root page when JSON is requested.
    session.headers.update({"User-Agent": "kopilkin-pytest"})
    return session


@pytest.fixture
def registered_user(http: requests.Session) -> dict:
    password = "TestPass123!"
    payload = {
        "email": unique_email(),
        "password": password,
        "name": "Pytest User",
    }

    # Use auth-service directly to avoid exhausting API Gateway rate limit.
    response = http.post(f"{AUTH_URL}/register", json=payload, timeout=20)
    assert_status(response, 200)
    user = response.json()

    login_response = http.post(
        f"{AUTH_URL}/login",
        json={"email": payload["email"], "password": password},
        timeout=20,
    )
    assert_status(login_response, 200)
    login_data = login_response.json()

    return {
        "id": user["id"],
        "email": payload["email"],
        "password": password,
        "name": payload["name"],
        "access_token": login_data["access_token"],
    }


def create_transaction(
    http: requests.Session,
    user_id: str,
    amount: float,
    category: str,
    tx_type: str,
    description: str | None = None,
    tx_id: str | None = None,
) -> dict:
    payload = {
        "user_id": user_id,
        "amount": amount,
        "category": category,
        "type": tx_type,
        "description": description or f"Pytest {category}",
        "date": "2026-06-01",
    }
    if tx_id:
        payload["id"] = tx_id

    # Use transaction-service directly; gRPC is tested separately through gateway.
    response = http.post(f"{TRANSACTION_URL}/transactions", json=payload, timeout=20)
    assert_status(response, 200)
    return response.json()


def create_goal(
    http: requests.Session,
    user_id: str,
    title: str | None = None,
    target_amount: float = 1000,
) -> dict:
    payload = {
        "user_id": user_id,
        "title": title or f"Pytest Goal {uuid.uuid4().hex[:6]}",
        "target_amount": target_amount,
    }
    # Use savings-service directly; CreateGoalOperation gRPC is tested via gateway.
    response = http.post(f"{SAVINGS_URL}/goals", json=payload, timeout=20)
    assert_status(response, 200)
    return response.json()


def get_goal_by_id(http: requests.Session, user_id: str, goal_id: str) -> dict | None:
    response = http.get(f"{SAVINGS_URL}/goals/{user_id}", timeout=20)
    assert_status(response, 200)
    goals = response.json()
    return next((goal for goal in goals if goal["id"] == goal_id), None)


def get_goal_operation(http: requests.Session, goal_id: str, operation_id: str) -> dict | None:
    response = http.get(f"{SAVINGS_URL}/goals/{goal_id}/operations", timeout=20)
    assert_status(response, 200)
    operations = response.json()
    return next((operation for operation in operations if operation["id"] == operation_id), None)


def get_user_transactions(http: requests.Session, user_id: str) -> list[dict]:
    response = http.get(f"{TRANSACTION_URL}/transactions/{user_id}", timeout=20)
    assert_status(response, 200)
    return response.json()
