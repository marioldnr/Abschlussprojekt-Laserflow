"""Tests: Sind die ECHTEN Endpunkte der App durch Anmeldung und Rolle geschützt? (US03)

US03 verlangt: "Die Berechtigung wird bei jeder Anfrage auf dem Server geprüft; Zugriffe
auf Funktionen einer anderen Rolle werden abgelehnt."

Abgrenzung zu tests/test_dependencies.py: Dort prüft Mario die Bausteine require_roles,
require_employee und require_admin an eigenen Test-Endpunkten. Hier wird die echte App
aus app/main.py benutzt. So fällt auf, wenn ein echter Endpunkt den Schutz vergisst.

Die Datenbank ist eine leere SQLite-Datenbank im Arbeitsspeicher (nie Neon, siehe conftest.py).
Benötigt das Paket httpx (für den TestClient von FastAPI).
"""

import re

import pytest

pytest.importorskip("httpx", reason="Für die Endpunkt-Tests: pip install httpx")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.accounts import employee_service  # noqa: E402
from app.accounts.models import User  # noqa: E402
from app.accounts.service import hash_password  # noqa: E402
from app.database import get_db, init_db  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "geheim123"
ADMIN = "admin@example.de"
EMPLOYEE = "mia@example.de"
CUSTOMER = "kunde@example.de"


@pytest.fixture
def client():
    """TestClient auf die echte App, mit eigener Datenbank im Arbeitsspeicher.

    Konten: Admin, Mitarbeiter, Kunde (alle bestätigt).
    StaticPool: Der TestClient arbeitet in einem anderen Thread; ohne StaticPool
    sähe er eine andere, leere Datenbank.
    """
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False)

    db = factory()
    employee_service.create_employee(db, ADMIN, PASSWORD, "Ada", "Admin", "admin")
    employee_service.create_employee(db, EMPLOYEE, PASSWORD, "Mia", "Mitarbeiter", "employee")
    db.add(User(email=CUSTOMER, password_hash=hash_password(PASSWORD), role="customer", is_verified=True))
    db.commit()
    db.close()

    def override_get_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def login(client, email):
    """Meldet an; das Sitzungs-Cookie bleibt im TestClient für die nächsten Anfragen."""
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text


def api_routes(prefix):
    """Alle echten Routen der App unter prefix als Liste von (Methode, Pfad).

    Gelesen aus der OpenAPI-Beschreibung der App (dieselbe Quelle wie /docs). Das ist
    unabhängig davon, wie FastAPI eingebundene Router intern speichert.
    Pfad-Parameter wie {employee_id} werden durch 1 ersetzt.
    """
    found = []
    for path, operations in app.openapi()["paths"].items():
        if path.startswith(prefix):
            for method in sorted(operations):
                found.append((method.upper(), re.sub(r"\{[^}]+\}", "1", path)))
    return found


ADMIN_ROUTES = api_routes("/api/admin/")
ACCOUNT_ROUTES = api_routes("/api/account")


def call(client, method, path):
    """Ruft eine Route auf; POST/PUT bekommen einen leeren JSON-Body."""
    kwargs = {"json": {}} if method in {"POST", "PUT", "PATCH"} else {}
    return client.request(method, path, **kwargs)


# --------------------------------------------------------------------------- Absicherung der Testliste


def test_routes_were_found():
    """Schutz gegen einen leeren Test: Die App muss Admin- und Konto-Routen haben."""
    assert ADMIN_ROUTES, "keine Routen unter /api/admin/ gefunden"
    assert ACCOUNT_ROUTES, "keine Routen unter /api/account gefunden"


# --------------------------------------------------------------------------- ohne Anmeldung -> 401


@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES + ACCOUNT_ROUTES)
def test_every_protected_route_needs_login(client, method, path):
    """Jede Admin- und Konto-Route lehnt Anfragen ohne Anmeldung mit 401 ab."""
    assert call(client, method, path).status_code == 401


def test_who_am_i_without_login_gives_401(client):
    assert client.get("/api/auth/me").status_code == 401


# --------------------------------------------------------------------------- Kunde und Mitarbeiter -> 403 bei Admin-Funktionen


@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_customer_gets_403_on_every_admin_route(client, method, path):
    login(client, CUSTOMER)
    assert call(client, method, path).status_code == 403


@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_employee_gets_403_on_every_admin_route(client, method, path):
    login(client, EMPLOYEE)
    assert call(client, method, path).status_code == 403


# --------------------------------------------------------------------------- erlaubte Zugriffe


def test_admin_may_list_employees(client):
    login(client, ADMIN)
    response = client.get("/api/admin/employees")
    assert response.status_code == 200
    emails = {e["email"] for e in response.json()}
    assert {ADMIN, EMPLOYEE} <= emails


@pytest.mark.parametrize("email", [CUSTOMER, EMPLOYEE, ADMIN])
def test_every_role_may_see_own_account(client, email):
    """Mein Konto ist für jede angemeldete Rolle erreichbar und zeigt das eigene Konto."""
    login(client, email)
    response = client.get("/api/account")
    assert response.status_code == 200
    assert response.json()["email"] == email


@pytest.mark.parametrize("email", [CUSTOMER, EMPLOYEE, ADMIN])
def test_who_am_i_shows_own_role(client, email):
    login(client, email)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == email
