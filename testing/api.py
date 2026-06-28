from fastapi.testclient import TestClient
from backend.main import app
from backend.db.db import get_db

class MockSession:
    def add(self, *args, **kwargs): pass
    def commit(self): pass
    def rollback(self): pass
    def query(self, *args, **kwargs): return self
    def order_by(self, *args, **kwargs): return self
    def limit(self, *args, **kwargs): return self
    def all(self): return []

def override_get_db():
    yield MockSession()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_ingest_live_success():
    payload = {
        "order_id": "ORD-1234",
        "order_status": "delivered",
        "payment_value": 150.50,
        "timestamp": "2023-10-01T12:00:00Z"
    }
    headers = {"X-API-Key": "dev-secret-key-123"} 
    
    response = client.post("/ingest", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_get_registry():
    response = client.get("/registry")
    assert response.status_code == 200
    assert "data" in response.json()