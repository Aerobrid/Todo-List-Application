from fastapi.testclient import TestClient
from app.security import read_rate_limiter, write_rate_limiter

def test_api_create_task(client: TestClient) -> None:
    """
    Tests POST /api/tasks endpoint, validating response codes and data serialization.
    """
    payload = {
        "title": "Setup pytest suite",
        "description": "Establish mock client connections",
        "priority": "high",
        "category": "work"
    }
    
    response = client.post("/api/tasks/", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["id"] is not None
    assert data["title"] == "Setup pytest suite"
    assert data["is_completed"] is False

def test_api_validation_boundaries(client: TestClient) -> None:
    """
    Checks that malformed payloads (e.g. blank titles) are blocked by validation rules.
    """
    # 1. Title missing
    response = client.post("/api/tasks/", json={"description": "No title"})
    assert response.status_code == 422  # Unprocessable Entity
    
    # 2. Empty string or whitespace-only title
    response_empty = client.post("/api/tasks/", json={"title": "   "})
    assert response_empty.status_code == 422

    # 3. Title too long (exceeds 100 characters)
    long_title = "a" * 101
    response_long = client.post("/api/tasks/", json={"title": long_title})
    assert response_long.status_code == 422

def test_api_read_tasks(client: TestClient) -> None:
    """
    Validates GET /api/tasks endpoint.
    """
    # Seed a task first
    client.post("/api/tasks/", json={"title": "Task A"})
    
    response = client.get("/api/tasks/")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["title"] == "Task A"

def test_api_xss_defense(client: TestClient) -> None:
    """
    Verifies that html tags are escaped during API ingestion to prevent XSS execution.
    """
    payload = {
        "title": "<script>alert('xss')</script>",
        "description": "<a href='javascript:exploit()'>click me</a>"
    }
    
    response = client.post("/api/tasks/", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    # verify dangerous brackets are neutralized
    assert "<script>" not in data["title"]
    assert "<a href=" not in data["description"]
    assert "&lt;script&gt;" in data["title"]
    assert "&lt;a href=" in data["description"]

def test_api_not_found(client: TestClient) -> None:
    """
    Asserts a request to non-existent task IDs yields a clean 404 response.
    """
    response = client.get("/api/tasks/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task with ID 99999 not found"

def test_api_rate_limiter(client: TestClient) -> None:
    """
    Validates that the rate limiter halts execution with HTTP 429 when client limits are hit.
    Resets history flags before and after to keep tests isolated.
    """
    # clear rate limiter bucket state before starting
    read_rate_limiter.history.clear()
    
    # write route limit is 30, read route limit is 100.
    # call read route 100 times, which should succeed
    for _ in range(100):
        response = client.get("/api/tasks/")
        assert response.status_code == 200
        
    # the 101st request from the same test client IP must trigger the rate limit block
    exceeded_response = client.get("/api/tasks/")
    assert exceeded_response.status_code == 429
    assert "rate limit exceeded" in exceeded_response.json()["detail"].lower()
    
    # clear state again to prevent bleeding block into other test runs
    read_rate_limiter.history.clear()

def test_api_clear_description(client: TestClient) -> None:
    """
    Verifies that a PUT request explicitly setting description to null (None)
    successfully clears the existing description in the database.
    """
    # 1. Seed task with description
    resp = client.post("/api/tasks/", json={
        "title": "Task with description",
        "description": "Initial text description"
    })
    assert resp.status_code == 201
    task_id = resp.json()["id"]
    assert resp.json()["description"] == "Initial text description"

    # 2. Update task, setting description explicitly to None (null)
    update_resp = client.put(f"/api/tasks/{task_id}", json={
        "description": None
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] is None

    # 3. Read task back and verify it is indeed empty (null) in database
    get_resp = client.get(f"/api/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["description"] is None

def test_api_ai_config(client: TestClient) -> None:
    """
    Validates GET /api/ai/config returns a dictionary indicating API status.
    """
    response = client.get("/api/ai/config")
    assert response.status_code == 200
    data = response.json()
    assert "has_api_key" in data
    assert isinstance(data["has_api_key"], bool)
