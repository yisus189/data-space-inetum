from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.main import create_app
from src.db.models import Base
from src.db.session import SessionLocal


# Use SQLite in-memory for tests with StaticPool to keep the database alive
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

app = create_app()

# override get_db to use testing session
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides = {}
from src.app.deps import get_db as real_get_db
app.dependency_overrides[real_get_db] = override_get_db

client = TestClient(app)

def test_create_and_get_participant():
    res = client.post("/participants/", json={"username": "alice", "display_name": "Alice"}, headers={"Authorization": "Bearer alice"})
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "alice"

    pid = data["id"]
    res2 = client.get(f"/participants/{pid}")
    assert res2.status_code == 200
    assert res2.json()["username"] == "alice"

def test_list_participants():
    res = client.get("/participants/")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(p["username"] == "alice" for p in data)