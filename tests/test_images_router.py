"""Tests für die Endpunkte unter /api/images (US04) über HTTP.

Eigene kleine App mit /api/auth (zum Anmelden) und /api/images, Datenbank im
Arbeitsspeicher, Bilder im Test-Ordner. Aufbau wie in test_account_router.py.
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
from app.accounts import service as accounts_service  # noqa: E402
from app.accounts.router import router as auth_router  # noqa: E402
from app.catalog.models import Product  # noqa: E402
from app.database import get_db, init_db  # noqa: E402
from app.images import service  # noqa: E402
from app.images.router import router as images_router  # noqa: E402

PASSWORD = "geheim123"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50


def register_body(email: str) -> dict:
    return {
        "email": email,
        "password": PASSWORD,
        "first_name": "Anna",
        "last_name": "Muster",
        "street": "Musterstraße",
        "house_number": "12",
        "postal_code": "12345",
        "city": "Musterstadt",
    }


@pytest.fixture
def sent_mails(monkeypatch):
    mails = []
    monkeypatch.setattr(accounts_service, "send_mail", lambda to, subject, body: mails.append(body))
    return mails


@pytest.fixture
def setup(sent_mails, tmp_path, monkeypatch):
    """App, Datenbank (StaticPool, damit alle Sessions dieselbe sehen) und ein Produkt."""
    monkeypatch.setattr(config, "UPLOAD_DIR", str(tmp_path))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False)

    with testing_session() as db:
        product = Product(name="Holzbrett", width_mm=300, height_mm=200, price_cent=2990)
        db.add(product)
        db.commit()
        product_id = product.id

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(images_router)
    app.dependency_overrides[get_db] = override_get_db
    yield app, product_id
    engine.dispose()


def login_as(app, sent_mails, email: str) -> TestClient:
    """Neuer Client, registriert und bestätigt (danach angemeldet)."""
    client = TestClient(app)
    client.post("/api/auth/register", json=register_body(email))
    code = re.search(r"Bestätigungscode lautet: (\d{4})", sent_mails[-1]).group(1)
    client.post("/api/auth/verify", json={"email": email, "code": code})
    return client


@pytest.fixture
def anna(setup, sent_mails):
    app, _ = setup
    return login_as(app, sent_mails, "anna@example.de")


@pytest.fixture
def product_id(setup):
    return setup[1]


def upload(client, product_id, content=PNG):
    return client.post(f"/api/images?product_id={product_id}", content=content, headers={"Content-Type": "image/png"})


# --------------------------------------------------------------------------- Anmeldung


@pytest.mark.parametrize(
    ("method", "path"),
    [("post", "/api/images?product_id=1"), ("get", "/api/images/1"), ("get", "/api/images/1/original")],
)
def test_without_login_gives_401(setup, method, path):
    app, _ = setup
    assert getattr(TestClient(app), method)(path).status_code == 401


# --------------------------------------------------------------------------- Normalfall


def test_upload_and_fetch_own_image(anna, product_id):
    response = upload(anna, product_id)
    assert response.status_code == 201
    data = response.json()
    assert data["product_id"] == product_id
    assert data["status"] == "uploaded"
    assert data["original_url"] == f"/api/images/{data['id']}/original"
    assert "original_path" not in data  # Speicher-Schlüssel bleibt intern

    assert anna.get(f"/api/images/{data['id']}").json()["id"] == data["id"]
    original = anna.get(data["original_url"])
    assert original.status_code == 200
    assert original.content == PNG
    assert original.headers["content-type"] == "image/png"


# --------------------------------------------------------------------------- ungültige Eingaben


def test_wrong_type_gives_422_with_message(anna, product_id):
    response = upload(anna, product_id, content=b"%PDF-1.4 ...")
    assert response.status_code == 422
    assert response.json()["detail"] == [{"loc": ["body", "image"], "msg": service.MSG_TYPE}]


def test_empty_file_gives_422(anna, product_id):
    response = upload(anna, product_id, content=b"")
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == service.MSG_EMPTY


def test_too_large_file_gives_422(anna, product_id):
    content = PNG + b"\x00" * service.MAX_BYTES
    response = upload(anna, product_id, content=content)
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == service.MSG_SIZE


def test_unknown_product_gives_404(anna):
    response = upload(anna, 999)
    assert response.status_code == 404
    assert response.json()["detail"] == service.MSG_PRODUCT_NOT_FOUND


def test_missing_product_id_gives_422(anna):
    response = anna.post("/api/images", content=PNG)
    assert response.status_code == 422


# --------------------------------------------------------------------------- nur eigene Bilder


def test_foreign_image_gives_404(setup, sent_mails, anna, product_id):
    app, _ = setup
    image_id = upload(anna, product_id).json()["id"]
    ben = login_as(app, sent_mails, "ben@example.de")

    assert ben.get(f"/api/images/{image_id}").status_code == 404
    assert ben.get(f"/api/images/{image_id}/original").status_code == 404
