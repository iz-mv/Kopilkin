from conftest import RECSYS_URL, assert_status, create_transaction


def test_recommendations_are_generated_from_real_transactions(http, registered_user):
    user_id = registered_user["id"]

    create_transaction(http, user_id, 1200, "Salary", "income", "Pytest salary")
    create_transaction(http, user_id, 700, "Restaurants", "expense", "Pytest restaurant spending")

    response = http.get(f"{RECSYS_URL}/recommendations/{user_id}", timeout=30)
    assert_status(response, 200)
    data = response.json()

    assert data["user_id"] == user_id
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) >= 1
    assert any("approach" in recommendation for recommendation in data["recommendations"])
