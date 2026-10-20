"""Tests für die Endpunkte unter /api/admin/employees (app/accounts/employee_router.py).

Schwerpunkt: Nur Admins kommen an die Mitarbeiterverwaltung. Angemeldet wird wie im
echten Ablauf über POST /api/auth/login, das Sitzungs-Cookie merkt sich der TestClient.

Benötigt das Paket httpx (für den TestClient von FastAPI): pip install httpx
"""

import pytest

pytest.importorskip("httpx", reason="Für die Endpunkt-Tests: pip install httpx")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.accounts import employee_service  # noqa: E402
from app.accounts.employee_router import router as employee_router  # noqa: E402
from app.accounts.models import User  # noqa: E402
from app.accounts.router import router as accounts_router  # noqa: E402
from app.accounts.service import hash_password  # noqa: E402
from app.database import get_db, init_db  # noqa: E402

NEW_EMPLOYEE = {
    "email": "max@example.de",
    "password": "geheim123",
    "first_name": "Max",
    "last_name": "Muster",
    "role": "employee",
}


@pytest.fixture
def session_factory():
    """Datenbank im Arbeitsspeicher, die TestClient und Test gemeinsam benutzen.

    StaticPool: Der TestClient arbeitet in einem anderen Thread. Ohne StaticPool hätte
    jeder Thread eine eigene, leere Datenbank im Arbeitsspeicher.
    """
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(bind=engine)
    yield sessionmaker(bind=engine, autoflush=False)
    engine.dispose()


@pytest.fixture
def client(session_factory):
    """TestClient mit Anmelde- und Mitarbeiter-Router und einem Admin, einem Mitarbeiter, einem Kunden."""
    db = session_factory()
    employee_service.create_employee(db, "admin@example.de", "geheim123", "Ada", "Admin", "admin")
    employee_service.create_employee(db, "mia@example.de", "geheim123", "Mia", "Mitarbeiter", "employee")
    db.add(User(email="kunde@example.de", password_hash=hash_password("geheim123"), role="customer", is_verified=True))
    db.commit()
    db.close()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app = FastAPI()
    app.include_router(accounts_router)
    app.include_router(employee_router)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


def login(client, email):
    """Meldet an. Das Sitzungs-Cookie speichert der TestClient für die nächsten Anfragen."""
    response = client.post("/api/auth/login", json={"email": email, "password": "geheim123"})
    assert response.status_code == 200


# --------------------------------------------------------------------------- Zugriff


def test_without_login_gives_401(client):
    response = client.get("/api/admin/employees")

    assert response.status_code == 401
    assert response.json()["detail"] == "Bitte melde dich an."  # Meldung von get_current_user
    assert client.post("/api/admin/employees", json=NEW_EMPLOYEE).status_code == 401


@pytest.mark.parametrize("email", ["mia@example.de", "kunde@example.de"])
def test_employee_and_customer_get_403(client, email):
    login(client, email)

    assert client.get("/api/admin/employees").status_code == 403
    assert client.post("/api/admin/employees", json=NEW_EMPLOYEE).status_code == 403
    assert client.put("/api/admin/employees/1", json={**NEW_EMPLOYEE, "is_active": True}).status_code == 403


# --------------------------------------------------------------------------- Admin


def test_admin_lists_employees_with_roles_without_customers(client):
    login(client, "admin@example.de")

    response = client.get("/api/admin/employees")

    assert response.status_code == 200
    assert {(e["email"], e["role"]) for e in response.json()} == {
        ("admin@example.de", "admin"),
        ("mia@example.de", "employee"),
    }
    assert all("password_hash" not in e for e in response.json())


def test_admin_creates_employee_who_can_log_in(client):
    login(client, "admin@example.de")

    response = client.post("/api/admin/employees", json=NEW_EMPLOYEE)

    assert response.status_code == 201
    assert response.json()["role"] == "employee"
    assert client.post("/api/auth/login", json={"email": "max@example.de", "password": "geheim123"}).status_code == 200


def test_create_with_invalid_fields_gives_422_with_field_names(client):
    login(client, "admin@example.de")

    response = client.post("/api/admin/employees", json={**NEW_EMPLOYEE, "email": "x", "role": "customer"})

    assert response.status_code == 422
    fields = {item["loc"][-1] for item in response.json()["detail"]}
    assert fields == {"email", "role"}


def test_create_with_taken_email_gives_409(client):
    login(client, "admin@example.de")
    assert client.post("/api/admin/employees", json={**NEW_EMPLOYEE, "email": "mia@example.de"}).status_code == 409


def test_admin_updates_employee(client):
    login(client, "admin@example.de")
    mia = next(e for e in client.get("/api/admin/employees").json() if e["email"] == "mia@example.de")

    response = client.put(
        f"/api/admin/employees/{mia['id']}",
        json={"email": "mia@example.de", "first_name": "Mia", "last_name": "Neu", "role": "admin", "is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["last_name"] == "Neu"
    assert response.json()["role"] == "admin"
    assert response.json()["is_active"] is False


def test_deactivated_employee_cannot_be_changed_again_gives_400(client):
    login(client, "admin@example.de")
    mia = next(e for e in client.get("/api/admin/employees").json() if e["email"] == "mia@example.de")
    url = f"/api/admin/employees/{mia['id']}"
    body = {"email": "mia@example.de", "first_name": "Mia", "last_name": "Mitarbeiter", "role": "employee"}

    assert client.put(url, json={**body, "is_active": False}).status_code == 200
    response = client.put(url, json={**body, "is_active": True})  # Reaktivieren ist nicht mehr möglich

    assert response.status_code == 400
    assert "deaktiviert" in response.json()["detail"]


def test_update_unknown_or_customer_gives_404(client):
    login(client, "admin@example.de")
    body = {**NEW_EMPLOYEE, "is_active": True}
    assert client.put("/api/admin/employees/999", json=body).status_code == 404
    assert client.get("/api/admin/employees/3").status_code == 404  # ID 3 = Kunde


def test_last_admin_cannot_demote_himself(client):
    login(client, "admin@example.de")
    ada = next(e for e in client.get("/api/admin/employees").json() if e["role"] == "admin")

    response = client.put(
        f"/api/admin/employees/{ada['id']}",
        json={"email": ada["email"], "first_name": "Ada", "last_name": "Admin", "role": "employee", "is_active": True},
    )

    assert response.status_code == 400
