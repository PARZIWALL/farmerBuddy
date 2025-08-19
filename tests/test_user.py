from app import create_app


def test_user_crud_flow():
    app = create_app("config.TestingConfig")
    client = app.test_client()

    # List should start empty
    resp = client.get("/api/users/")
    assert resp.status_code == 200
    assert resp.get_json() == []

    # Create a user
    resp = client.post("/api/users/", json={"name": "Alice"})
    assert resp.status_code == 201
    created = resp.get_json()
    assert created["name"] == "Alice"
    user_id = created["id"]

    # Fetch by id
    resp = client.get(f"/api/users/{user_id}")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Alice"


