"""Tests für die Endpunkte unter /api/account ("Mein Konto", US10) über HTTP.

Eigene kleine App mit beiden Routern (/api/auth und /api/account), Datenbank im
Arbeitsspeicher, Profilbilder im Test-Ordner. Benötigt httpx (pip install httpx).
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
from app.accounts import account_service, service  # noqa: E402
from app.accounts.account_router import router as account_router  # noqa: E402
from app.accounts.router import router as auth_router  # noqa: E402
from app.database import get_db, init_db  # noqa: E402

PASSWORD = "geheim123"
REGISTER_BODY = {
    "email": "anna@example.de",
    "password": PASSWORD,
    "first_name": "Anna",
    "last_name": "Muster",
    "street": "Musterstraße",
    "house_number": "12",
    "postal_code": "12345",
    "city": "Musterstadt",
}
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50


@pytest.fixture
def sent_mails(monkeypatch):
    mails = []

    def fake_send(to, subject, body):
        mails.append({"to": to, "body": body})

    monkeypatch.setattr(service, "send_mail", fake_send)
    monkeypatch.setattr(account_service, "send_mail", fake_send)
    return mails


@pytest.fixture
def client(sent_mails, tmp_path, monkeypatch):
    """TestClient mit leerer Datenbank (StaticPool, siehe test_accounts_router.py)."""
    monkeypatch.setattr(config, "UPLOAD_DIR", str(tmp_path))
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
    app.include_router(auth_router)
    app.include_router(account_router)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()


def last_code(sent_mails) -> str:
    return re.search(r"Bestätigungscode lautet: (\d{4})", sent_mails[-1]["body"]).group(1)


@pytest.fixture
def logged_in(client, sent_mails):
    """Registriert, bestätigt (= angemeldet) und gibt den Client zurück."""
    client.post("/api/auth/register", json=REGISTER_BODY)
    client.post("/api/auth/verify", json={"email": REGISTER_BODY["email"], "code": last_code(sent_mails)})
    return client


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/account"),
        ("put", "/api/account/profile"),
        ("put", "/api/account/password"),
        ("post", "/api/account/email"),
        ("get", "/api/account/avatar"),
        ("put", "/api/account/avatar"),
        ("post", "/api/account/delete"),
    ],
)
def test_all_endpoints_need_login(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def test_get_account(logged_in):
    data = logged_in.get("/api/account").json()
    assert data["email"] == "anna@example.de"
    assert (data["street"], data["house_number"]) == ("Musterstraße", "12")
    assert data["avatar_url"] is None
    assert "avatar_path" not in data  # Dateipfad bleibt intern


def test_update_profile(logged_in):
    body = {"first_name": "Anne", "last_name": "Neu", "street": "Am Ring", "house_number": "3a",
            "postal_code": "54321", "city": "Köln"}
    response = logged_in.put("/api/account/profile", json=body)
    assert response.status_code == 200
    assert response.json()["city"] == "Köln"
    assert logged_in.get("/api/auth/me").json()["first_name"] == "Anne"


def test_update_profile_field_error(logged_in):
    body = {"first_name": "Anne", "last_name": "Neu", "street": "Am Ring 3", "house_number": "3",
            "postal_code": "54321", "city": "Köln"}
    response = logged_in.put("/api/account/profile", json=body)
    assert response.status_code == 422
    assert [item["loc"][-1] for item in response.json()["detail"]] == ["street"]


def test_change_password_and_login_again(logged_in):
    response = logged_in.put("/api/account/password", json={"current_password": PASSWORD, "new_password": "neuesPw123"})
    assert response.status_code == 204
    assert logged_in.get("/api/account").status_code == 200  # diese Sitzung bleibt
    logged_in.post("/api/auth/logout")
    assert logged_in.post("/api/auth/login", json={"email": "anna@example.de", "password": "neuesPw123"}).status_code == 200


def test_email_change_flow(logged_in, sent_mails):
    response = logged_in.post("/api/account/email", json={"new_email": "neu@example.de", "password": PASSWORD})
    assert response.status_code == 202
    assert response.json() == {"pending_email": "neu@example.de"}
    assert logged_in.get("/api/account").json()["pending_email"] == "neu@example.de"

    response = logged_in.post("/api/account/email/verify", json={"code": last_code(sent_mails)})
    assert response.status_code == 200
    assert response.json()["email"] == "neu@example.de"
    assert response.json()["pending_email"] is None


def test_avatar_upload_show_remove(logged_in, tmp_path):
    response = logged_in.put("/api/account/avatar", content=PNG, headers={"Content-Type": "image/png"})
    assert response.status_code == 200
    url = response.json()["avatar_url"]
    assert url.startswith("/api/account/avatar?v=")

    assert logged_in.get("/api/auth/me").json()["avatar_url"] == url  # für das Icon oben
    image = logged_in.get(url)
    assert image.status_code == 200
    assert image.content == PNG

    assert logged_in.delete("/api/account/avatar").status_code == 204
    assert logged_in.get("/api/account/avatar").status_code == 404
    assert logged_in.get("/api/auth/me").json()["avatar_url"] is None


def test_avatar_wrong_type_gives_422(logged_in):
    response = logged_in.put("/api/account/avatar", content=b"%PDF-1.4 ...", headers={"Content-Type": "image/png"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "avatar"


def test_delete_account(logged_in):
    assert logged_in.post("/api/account/delete", json={"password": "falsch123"}).status_code == 422
    assert logged_in.get("/api/account").status_code == 200  # noch da

    assert logged_in.post("/api/account/delete", json={"password": PASSWORD}).status_code == 204
    assert logged_in.get("/api/account").status_code == 401  # abgemeldet
    response = logged_in.post("/api/auth/login", json={"email": "anna@example.de", "password": PASSWORD})
    assert response.status_code == 401
    # ohne laufende Bestellung sofort anonymisiert: die E-Mail ist wieder frei
    assert logged_in.post("/api/auth/register", json=REGISTER_BODY).status_code == 201
