"""Tests für die Rollenprüfung in app/accounts/dependencies.py (require_roles, require_employee, require_admin).

Schwerpunkt: Anmeldung (401) und Rolle (403) werden an einer Stelle geprüft. Die Tests
laufen über HTTP mit zwei Test-Endpunkten, die nur die Abhängigkeit benutzen.
Angemeldet wird wie im echten Ablauf über POST /api/auth/login.

Benötigt das Paket httpx (für den TestClient von FastAPI): pip install httpx
"""

import pytest

pytest.importorskip("httpx", reason="Für die Endpunkt-Tests: pip install httpx")

from fastapi import Depends, FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.accounts import employee_service  # noqa: E402
from app.accounts.dependencies import (  # noqa: E402
    MSG_ADMIN_ONLY,
    MSG_EMPLOYEE_ONLY,
    require_admin,
    require_employee,
    require_roles,
)
from app.accounts.models import User  # noqa: E402
from app.accounts.router import router as accounts_router  # noqa: E402
from app.accounts.service import hash_password  # noqa: E402
from app.database import get_db, init_db  # noqa: E402


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
    """TestClient mit Anmelde-Router und zwei Test-Endpunkten, je einer pro Abhängigkeit.

    Konten: Admin, Mitarbeiter, Kunde und ein Konto mit unbekannter Rolle "lieferant".
    """
    db = session_factory()
    employee_service.create_employee(db, "admin@example.de", "geheim123", "Ada", "Admin", "admin")
    employee_service.create_employee(db, "mia@example.de", "geheim123", "Mia", "Mitarbeiter", "employee")
    db.add(User(email="kunde@example.de", password_hash=hash_password("geheim123"), role="customer", is_verified=True))
    db.add(User(email="fremd@example.de", password_hash=hash_password("geheim123"), role="lieferant", is_verified=True))
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

    @app.get("/test/mitarbeiter")
    def mitarbeiter_only(user: User = Depends(require_employee)):
        """Test-Endpunkt: nur Mitarbeiter und Admin."""
        return {"role": user.role}

    @app.get("/test/admin")
    def admin_only(user: User = Depends(require_admin)):
        """Test-Endpunkt: nur Admin."""
        return {"role": user.role}

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


def login(client, email):
    """Meldet an. Das Sitzungs-Cookie speichert der TestClient für die nächsten Anfragen."""
    response = client.post("/api/auth/login", json={"email": email, "password": "geheim123"})
    assert response.status_code == 200


ENDPOINTS = ["/test/mitarbeiter", "/test/admin"]


# --------------------------------------------------------------------------- ohne Anmeldung


@pytest.mark.parametrize("path", ENDPOINTS)
def test_without_login_gives_401(client, path):
    """Ohne Anmeldung kommt 401, egal welche Rolle der Endpunkt verlangt."""
    response = client.get(path)

    assert response.status_code == 401
    assert response.json()["detail"] == "Bitte melde dich an."


# --------------------------------------------------------------------------- Kunde


def test_customer_gets_403_on_employee_endpoint_with_employee_message(client):
    """Kunde auf dem Mitarbeiter-Endpunkt: 403 mit der Mitarbeiter-Meldung."""
    login(client, "kunde@example.de")

    response = client.get("/test/mitarbeiter")

    assert response.status_code == 403
    assert response.json()["detail"] == MSG_EMPLOYEE_ONLY


def test_customer_gets_403_on_admin_endpoint_with_admin_message(client):
    """Kunde auf dem Admin-Endpunkt: 403 mit der Admin-Meldung."""
    login(client, "kunde@example.de")

    response = client.get("/test/admin")

    assert response.status_code == 403
    assert response.json()["detail"] == MSG_ADMIN_ONLY


# --------------------------------------------------------------------------- Mitarbeiter


def test_employee_may_use_employee_endpoint(client):
    """Mitarbeiter darf den Mitarbeiter-Endpunkt benutzen."""
    login(client, "mia@example.de")

    response = client.get("/test/mitarbeiter")

    assert response.status_code == 200
    assert response.json() == {"role": "employee"}


def test_employee_gets_403_on_admin_endpoint(client):
    """Mitarbeiter darf keine Admin-Seite benutzen (Akzeptanzkriterium US15)."""
    login(client, "mia@example.de")

    response = client.get("/test/admin")

    assert response.status_code == 403
    assert response.json()["detail"] == MSG_ADMIN_ONLY


# --------------------------------------------------------------------------- Admin


@pytest.mark.parametrize("path", ENDPOINTS)
def test_admin_may_use_both_endpoints(client, path):
    """Admin hat alle Mitarbeiterrechte, deshalb darf er beide Endpunkte benutzen."""
    login(client, "admin@example.de")

    response = client.get(path)

    assert response.status_code == 200
    assert response.json() == {"role": "admin"}


# --------------------------------------------------------------------------- unbekannte Rolle


@pytest.mark.parametrize("path", ENDPOINTS)
def test_unknown_role_gets_403_everywhere(client, path):
    """Eine Rolle, die nirgends aufgezählt ist, bekommt überall 403 (nichts ist standardmäßig erlaubt)."""
    login(client, "fremd@example.de")

    assert client.get(path).status_code == 403


# --------------------------------------------------------------------------- Aufbau der Fabrik


def test_require_roles_without_roles_raises_value_error():
    """Ohne Rolle schlägt der Aufbau sofort fehl, nicht erst bei einer Anfrage."""
    with pytest.raises(ValueError, match="mindestens eine Rolle"):
        require_roles()
