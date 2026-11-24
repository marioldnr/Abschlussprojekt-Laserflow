"""Tests für die Endpunkte unter /api/products (app/catalog/router.py).

Schwerpunkt: Der Katalog ist ohne Anmeldung lesbar, nur Mitarbeiter und Admins dürfen
Produkte als ausverkauft markieren. Angemeldet wird wie im echten Ablauf über
POST /api/auth/login, das Sitzungs-Cookie merkt sich der TestClient.

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
from app.accounts.models import User  # noqa: E402
from app.accounts.router import router as accounts_router  # noqa: E402
from app.accounts.service import hash_password  # noqa: E402
from app.catalog import service as catalog_service  # noqa: E402
from app.catalog.router import router as catalog_router  # noqa: E402
from app.database import get_db, init_db  # noqa: E402

PASSWORD = "geheim123"
PUBLIC_FIELDS = {
    "id",
    "name",
    "description",
    "short_description",
    "width_mm",
    "height_mm",
    "depth_mm",
    "price_cent",
    "product_type",
    "engraving_width_mm",
    "engraving_height_mm",
    "is_sold_out",
    "images",
}


@pytest.fixture
def session_factory():
    """Datenbank im Arbeitsspeicher, die TestClient und Test gemeinsam benutzen (StaticPool, siehe test_employee_router.py)."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(bind=engine)
    yield sessionmaker(bind=engine, autoflush=False)
    engine.dispose()


@pytest.fixture
def client(session_factory):
    """TestClient mit Anmelde- und Katalog-Router, einem Admin, einem Mitarbeiter, einem Kunden und Produkten."""
    db = session_factory()
    employee_service.create_employee(db, "admin@example.de", PASSWORD, "Ada", "Admin", "admin")
    employee_service.create_employee(db, "mia@example.de", PASSWORD, "Mia", "Mitarbeiter", "employee")
    db.add(User(email="kunde@example.de", password_hash=hash_password(PASSWORD), role="customer", is_verified=True))
    db.commit()

    catalog_service.create_product(
        db,
        name="Sichtbar",
        description="Erster Satz. Zweiter Satz.",
        width_mm=115,
        height_mm=95,
        depth_mm=110,
        price_cent=2490,
        product_type=catalog_service.PRODUCT_TYPE_FINISHED,
        image_paths=["img/a.webp", "img/b.webp"],
    )
    hidden = catalog_service.create_product(
        db,
        name="Versteckt",
        description="Geheim.",
        width_mm=1,
        height_mm=1,
        depth_mm=None,
        price_cent=100,
        product_type=catalog_service.PRODUCT_TYPE_FINISHED,
    )
    hidden.is_hidden = True
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
    app.include_router(catalog_router)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


def login(client, email):
    """Meldet an. Das Sitzungs-Cookie speichert der TestClient für die nächsten Anfragen."""
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200


# --------------------------------------------------------------------------- Liste


def test_list_without_login_gives_200_and_hides_hidden_products(client):
    response = client.get("/api/products")

    assert response.status_code == 200
    assert [p["name"] for p in response.json()] == ["Sichtbar"]


def test_list_contains_only_public_fields(client):
    product = client.get("/api/products").json()[0]

    assert set(product) == PUBLIC_FIELDS
    for internal in ("cad_template_path", "laser_program_path", "laser_settings", "is_hidden", "created_at"):
        assert internal not in product


def test_short_description_is_first_sentence_and_images_in_order(client):
    product = client.get("/api/products").json()[0]

    assert product["short_description"] == "Erster Satz."
    assert product["description"] == "Erster Satz. Zweiter Satz."
    assert product["images"] == ["img/a.webp", "img/b.webp"]


# --------------------------------------------------------------------------- Einzeln


def test_get_one_visible_product_gives_200(client):
    response = client.get("/api/products/1")

    assert response.status_code == 200
    assert response.json()["name"] == "Sichtbar"


def test_get_unknown_product_gives_404_with_message(client):
    response = client.get("/api/products/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Dieses Produkt gibt es nicht."


def test_get_hidden_product_gives_404(client):
    assert client.get("/api/products/2").status_code == 404


# --------------------------------------------------------------------------- Ausverkauft


def test_sold_out_without_login_gives_401(client):
    assert client.put("/api/products/1/sold-out", json={"is_sold_out": True}).status_code == 401


def test_sold_out_customer_gives_403(client):
    login(client, "kunde@example.de")

    assert client.put("/api/products/1/sold-out", json={"is_sold_out": True}).status_code == 403


def test_employee_marks_sold_out_and_get_shows_it(client):
    login(client, "mia@example.de")

    response = client.put("/api/products/1/sold-out", json={"is_sold_out": True})

    assert response.status_code == 200
    assert response.json()["is_sold_out"] is True
    assert client.get("/api/products/1").json()["is_sold_out"] is True


def test_admin_may_mark_sold_out(client):
    login(client, "admin@example.de")

    assert client.put("/api/products/1/sold-out", json={"is_sold_out": False}).status_code == 200


def test_sold_out_unknown_id_gives_404(client):
    login(client, "admin@example.de")

    assert client.put("/api/products/999/sold-out", json={"is_sold_out": True}).status_code == 404


def test_sold_out_on_hidden_product_is_allowed_for_employee(client):
    login(client, "mia@example.de")

    response = client.put("/api/products/2/sold-out", json={"is_sold_out": True})

    assert response.status_code == 200
    assert response.json()["is_sold_out"] is True
    assert response.json()["is_hidden"] is True


def test_sold_out_without_field_gives_422(client):
    login(client, "admin@example.de")

    assert client.put("/api/products/1/sold-out", json={}).status_code == 422


# --------------------------------------------------------------------------- Verwaltung (Liste)


def test_manage_without_login_gives_401(client):
    assert client.get("/api/products/manage").status_code == 401


def test_manage_as_customer_gives_403(client):
    login(client, "kunde@example.de")

    assert client.get("/api/products/manage").status_code == 403


def test_manage_as_employee_lists_hidden_products_with_flag(client):
    login(client, "mia@example.de")

    response = client.get("/api/products/manage")

    assert response.status_code == 200
    by_name = {p["name"]: p for p in response.json()}
    assert set(by_name) == {"Sichtbar", "Versteckt"}
    assert by_name["Sichtbar"]["is_hidden"] is False
    assert by_name["Versteckt"]["is_hidden"] is True


def test_manage_route_is_not_read_as_product_id(client):
    """Steht GET /manage hinter GET /{product_id}, käme 422 (Zahl erwartet). Hier muss 401 kommen, nicht 422."""
    assert client.get("/api/products/manage").status_code == 401


# --------------------------------------------------------------------------- Ausblenden


def test_hidden_without_login_gives_401(client):
    assert client.put("/api/products/1/hidden", json={"is_hidden": True}).status_code == 401


def test_hidden_as_customer_gives_403(client):
    login(client, "kunde@example.de")

    assert client.put("/api/products/1/hidden", json={"is_hidden": True}).status_code == 403


def test_employee_hides_product_and_it_disappears_from_catalog(client):
    login(client, "mia@example.de")

    response = client.put("/api/products/1/hidden", json={"is_hidden": True})

    assert response.status_code == 200
    assert response.json()["is_hidden"] is True
    assert client.get("/api/products").json() == []
    assert client.get("/api/products/1").status_code == 404


def test_employee_shows_hidden_product_again(client):
    login(client, "mia@example.de")

    response = client.put("/api/products/2/hidden", json={"is_hidden": False})

    assert response.status_code == 200
    assert response.json()["is_hidden"] is False
    assert [p["name"] for p in client.get("/api/products").json()] == ["Sichtbar", "Versteckt"]
    assert client.get("/api/products/2").status_code == 200


def test_admin_may_hide_product(client):
    login(client, "admin@example.de")

    assert client.put("/api/products/1/hidden", json={"is_hidden": True}).status_code == 200


def test_hidden_unknown_id_gives_404(client):
    login(client, "admin@example.de")

    assert client.put("/api/products/999/hidden", json={"is_hidden": True}).status_code == 404


def test_hidden_without_field_gives_422(client):
    login(client, "admin@example.de")

    assert client.put("/api/products/1/hidden", json={}).status_code == 422
