import requests

from conftest import (
    AGENT_URL,
    AUTH_URL,
    FRONTEND_URL,
    GATEWAY_URL,
    KAFKA_UI_URL,
    RECSYS_URL,
    SAVINGS_URL,
    TRANSACTION_URL,
    assert_status,
    clear_gateway_rate_limit_keys,
)


def test_gateway_health(http):
    clear_gateway_rate_limit_keys()
    response = http.get(f"{GATEWAY_URL}/health", timeout=10)
    assert_status(response, 200)
    data = response.json()
    assert data["service"] == "api-gateway"
    assert data["status"] == "running"


def test_core_services_are_running(http):
    services = [
        (AUTH_URL, "auth-service"),
        (TRANSACTION_URL, "transaction-service"),
        (SAVINGS_URL, "savings-service"),
        (RECSYS_URL, "recsys-service"),
    ]

    for base_url, service_name in services:
        response = http.get(f"{base_url}/", timeout=10)
        assert_status(response, 200)
        data = response.json()
        assert data["service"] == service_name
        assert data["status"] == "running"


def test_agent_health_and_metrics_are_available(http):
    response = http.get(f"{AGENT_URL}/health", timeout=10)
    assert_status(response, 200)
    assert response.json()["status"] == "healthy"

    metrics_response = http.get(f"{AGENT_URL}/metrics", timeout=10)
    assert_status(metrics_response, 200)
    assert "kopilkin_agent_chat_requests_total" in metrics_response.text


def test_frontend_and_kafka_ui_are_reachable(http):
    frontend_response = requests.get(
        FRONTEND_URL,
        headers={"Accept": "text/html,*/*", "User-Agent": "kopilkin-pytest"},
        timeout=10,
    )
    assert_status(frontend_response, 200)
    assert "html" in frontend_response.text.lower()

    kafka_ui_response = requests.get(
        KAFKA_UI_URL,
        headers={"Accept": "text/html,*/*", "User-Agent": "kopilkin-pytest"},
        timeout=10,
    )
    # Kafka UI may return 200 for the SPA root or 406 depending on Accept/content
    # negotiation. Both prove that the Kafka UI service is reachable.
    assert kafka_ui_response.status_code in (200, 302, 401, 403, 406)
