from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import create_app
from app.services.ampa_service import AMPAService

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "backend" / "ml" / "artifacts" / "ampa.npz"


def make_app():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return create_app(database_engine=engine, ampa_service=AMPAService(ARTIFACT))


def register(client, name, username):
    return client.post("/api/auth/register", json={"name": name, "username": username, "password": "secret123"})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_login_and_me_round_trip():
    with TestClient(make_app()) as client:
        created = register(client, "Sam Learner", "Sam.Learner")
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["user"]["role"] == "student"
        assert body["user"]["username"] == "sam.learner"
        assert body["user"]["name"] == "Sam Learner"
        assert body["user"]["student_id"] is not None

        me = client.get("/api/auth/me", headers=bearer(body["token"]))
        assert me.status_code == 200
        assert me.json()["username"] == "sam.learner"

        signed_out = client.post("/api/auth/logout", headers=bearer(body["token"]))
        assert signed_out.status_code == 200
        assert client.get("/api/auth/me", headers=bearer(body["token"])).status_code == 401

        login = client.post("/api/auth/login", json={"username": "sam.learner", "password": "secret123"})
        assert login.status_code == 200


def test_protected_routes_require_a_session():
    with TestClient(make_app()) as client:
        assert client.get("/api/questions").status_code == 401
        assert client.get("/api/students/1").status_code == 401
        assert client.get("/api/research/model").status_code == 401


def test_duplicate_username_and_bad_password_are_rejected():
    with TestClient(make_app()) as client:
        assert register(client, "First", "learner").status_code == 201
        assert register(client, "Second", "learner").status_code == 409
        bad = client.post("/api/auth/login", json={"username": "learner", "password": "wrong"})
        assert bad.status_code == 401


def test_students_cannot_read_each_others_data_or_research():
    with TestClient(make_app()) as client:
        first = register(client, "First", "first").json()
        second = register(client, "Second", "second").json()
        first_id, second_id = first["user"]["student_id"], second["user"]["student_id"]

        assert client.get(f"/api/students/{first_id}", headers=bearer(first["token"])).status_code == 200
        assert client.get(f"/api/students/{second_id}", headers=bearer(first["token"])).status_code == 403
        assert client.get("/api/research/model", headers=bearer(first["token"])).status_code == 403

        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"}).json()
        admin = bearer(login["token"])
        assert login["user"]["role"] == "admin"
        assert client.get(f"/api/students/{second_id}", headers=admin).status_code == 200
        assert client.get("/api/research/model", headers=admin).status_code == 200
