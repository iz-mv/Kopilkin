from conftest import AUTH_URL, TINY_PNG_BYTES, assert_status, unique_email


def test_register_login_me_logout_blacklist_flow(http):
    password = "TestPass123!"
    email = unique_email("auth-flow")

    register_response = http.post(
        f"{AUTH_URL}/register",
        json={"email": email, "password": password, "name": "Auth Flow User"},
        timeout=20,
    )
    assert_status(register_response, 200)
    user = register_response.json()
    assert user["email"] == email
    assert "password" not in user
    assert "password_hash" not in user

    login_response = http.post(
        f"{AUTH_URL}/login",
        json={"email": email, "password": password},
        timeout=20,
    )
    assert_status(login_response, 200)
    login = login_response.json()
    token = login["access_token"]
    assert token
    assert login["token_type"] == "bearer"

    me_response = http.get(
        f"{AUTH_URL}/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    assert_status(me_response, 200)
    assert me_response.json()["id"] == user["id"]

    logout_response = http.post(
        f"{AUTH_URL}/logout",
        json={"access_token": token},
        timeout=20,
    )
    assert_status(logout_response, 200)

    rejected_response = http.get(
        f"{AUTH_URL}/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    assert_status(rejected_response, 401)


def test_avatar_upload_uses_minio_and_updates_profile(http, registered_user):
    token = registered_user["access_token"]

    response = http.post(
        f"{AUTH_URL}/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("avatar.png", TINY_PNG_BYTES, "image/png")},
        timeout=30,
    )
    assert_status(response, 200)
    data = response.json()

    assert data["id"] == registered_user["id"]
    assert data["avatar_url"]
    assert "kopilkin-files" in data["avatar_url"]
    assert "avatars" in data["avatar_url"]
