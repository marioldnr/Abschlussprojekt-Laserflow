"""Tests für die Endpunkte unter /api/auth (app/accounts/router.py).

Hier wird der ganze Weg über HTTP getestet: Registrieren → Code bestätigen → angemeldet →
abmelden → wieder anmelden. Die Tests benutzen eine eigene kleine App nur mit diesem
Router und eine Datenbank im Arbeitsspeicher, nie die echte laserflow.db.

Benötigt das Paket httpx (für den TestClient von FastAPI): pip install httpx
"""

import re

import pytest

pytest.importorskip("httpx", reason="Für die Endpunkt-Tests: pip install httpx")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import config  # noqa: E402
from app.accounts import service  # noqa: E402
from app.accounts.router import router  # noqa: E402
from app.database import get_db, init_db  # noqa: E402

REGISTER_BODY = {
    "email": "anna@example.de",
    "password": "geheim123",
    "first_name": "Anna",
    "last_name": "Muster",
    "street": "Musterstraße",
    "house_number": "12",
    "postal_code": "12345",
    "city": "Musterstadt",
}


@pytest.fixture
def sent_mails(monkeypatch):
    """Fängt alle E-Mails ab, statt sie zu verschicken."""
    mails = []
    monkeypatch.setattr(service, "send_mail", lambda to, subject, body: mails.append(body))
    return mails


@pytest.fixture
def client(sent_mails):
    """TestClient mit eigener App und leerer Datenbank im Arbeitsspeicher.

    StaticPool: Der TestClient arbeitet in einem anderen Thread. Ohne StaticPool hätte
    jeder Thread eine eigene, leere Datenbank im Arbeitsspeicher.
    """
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()


def last_code(sent_mails) -> str:
    """Code aus der zuletzt "verschickten" E-Mail."""
    return re.search(r"Bestätigungscode lautet: (\d{4})", sent_mails[-1]).group(1)


def test_full_flow_register_verify_me_logout_login(client, sent_mails):
    # 1. Registrieren
    response = client.post("/api/auth/register", json=REGISTER_BODY)
    assert response.status_code == 201
    assert response.json()["email"] == "anna@example.de"
    assert len(sent_mails) == 1

    # vor dem Bestätigen: nicht angemeldet, Anmelden geht noch nicht
    assert client.get("/api/auth/me").status_code == 401
    response = client.post("/api/auth/login", json={"email": "anna@example.de", "password": "geheim123"})
    assert response.status_code == 403

    # 2. Code bestätigen → danach angemeldet
    response = client.post("/api/auth/verify", json={"email": "anna@example.de", "code": last_code(sent_mails)})
    assert response.status_code == 200
    assert response.json()["first_name"] == "Anna"
    assert "password_hash" not in response.json()
    assert config.SESSION_COOKIE_NAME in response.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "anna@example.de"

    # 3. Abmelden
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401

    # 4. Wieder anmelden
    response = client.post("/api/auth/login", json={"email": "Anna@Example.de", "password": "geheim123"})
    assert response.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_register_invalid_fields_give_422_with_field_names(client, sent_mails):
    body = {**REGISTER_BODY, "password": "kurz", "postal_code": "123"}
    response = client.post("/api/auth/register", json=body)

    assert response.status_code == 422
    fields = {item["loc"][-1]: item["msg"] for item in response.json()["detail"]}
    assert set(fields) == {"password", "postal_code"}
    assert "mindestens 8 Zeichen" in fields["password"]
    assert sent_mails == []


def test_register_wrong_house_number_is_reported_at_that_field(client):
    response = client.post("/api/auth/register", json={**REGISTER_BODY, "house_number": "12-14"})
    assert response.status_code == 422
    assert [item["loc"][-1] for item in response.json()["detail"]] == ["house_number"]


def test_register_missing_field_gives_422(client):
    body = {key: value for key, value in REGISTER_BODY.items() if key != "city"}
    assert client.post("/api/auth/register", json=body).status_code == 422


def test_register_same_email_twice_gives_409(client):
    client.post("/api/auth/register", json=REGISTER_BODY)
    response = client.post("/api/auth/register", json={**REGISTER_BODY, "email": "ANNA@example.de"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Diese E-Mail-Adresse ist bereits registriert."


def test_wrong_code_gives_400_and_no_cookie(client, sent_mails):
    client.post("/api/auth/register", json=REGISTER_BODY)
    wrong = "0000" if last_code(sent_mails) != "0000" else "1111"

    response = client.post("/api/auth/verify", json={"email": "anna@example.de", "code": wrong})
    assert response.status_code == 400
    assert "Der Code ist falsch" in response.json()["detail"]
    assert config.SESSION_COOKIE_NAME not in response.cookies
    assert client.get("/api/auth/me").status_code == 401


def test_resend_code_always_204(client, sent_mails):
    client.post("/api/auth/register", json=REGISTER_BODY)
    assert client.post("/api/auth/resend-code", json={"email": "anna@example.de"}).status_code == 204
    assert len(sent_mails) == 2
    # unbekannte Adresse: gleiche Antwort, aber keine E-Mail
    assert client.post("/api/auth/resend-code", json={"email": "niemand@example.de"}).status_code == 204
    assert len(sent_mails) == 2


def test_login_wrong_password_gives_401(client, sent_mails):
    client.post("/api/auth/register", json=REGISTER_BODY)
    client.post("/api/auth/verify", json={"email": "anna@example.de", "code": last_code(sent_mails)})
    client.post("/api/auth/logout")

    response = client.post("/api/auth/login", json={"email": "anna@example.de", "password": "falsch123"})
    assert response.status_code == 401
    assert response.json()["detail"] == "E-Mail-Adresse oder Passwort ist falsch."


def test_logout_without_session_is_fine(client):
    assert client.post("/api/auth/logout").status_code == 204
