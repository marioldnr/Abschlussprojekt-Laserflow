"""Tests für die Datenbank-Grundstruktur (alle Tabellen und ihre Beziehungen)."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.accounts.models import Address, User, VerificationCode
from app.catalog.models import Product, ProductImage
from app.images.models import CustomerImage
from app.orders.models import CartItem, Order, OrderItem
from app.production.models import ProductionFile, ProductionJob

EXPECTED_TABLES = {
    "users", "verification_codes", "addresses", "sessions",
    "products", "product_images",
    "customer_images",
    "cart_items", "orders", "order_items",
    "production_jobs", "production_files",
}


def make_user(db, email="kunde@example.de"):
    """Legt einen Test-Kunden an und gibt ihn zurück."""
    user = User(email=email, password_hash="hash")
    db.add(user)
    db.commit()
    return user


def make_product(db):
    """Legt ein Test-Produkt an und gibt es zurück."""
    product = Product(name="Holzbrett", width_mm=300, height_mm=200, price_cent=2499)
    db.add(product)
    db.commit()
    return product


# Normalfall

def test_all_tables_are_created(db):
    """init_db legt alle 11 Tabellen an."""
    assert set(inspect(db.get_bind()).get_table_names()) == EXPECTED_TABLES


def test_user_defaults(db):
    """Ein neuer User ist Kunde, aktiv, aber noch nicht bestätigt."""
    user = make_user(db)
    assert user.role == "customer"
    assert user.is_verified is False
    assert user.is_active is True
    assert user.created_at is not None


def test_user_with_address_and_verification_code(db):
    """Adresse und Bestätigung hängen über die Beziehung am User."""
    user = make_user(db)
    user.addresses.append(Address(street="Hauptstraße 1", postal_code="12345", city="Berlin"))
    user.verification_codes.append(VerificationCode(code="1234"))
    db.commit()
    assert user.addresses[0].user_id == user.id
    assert user.verification_codes[0].used_at is None


def test_complete_order_flow(db):
    """Einmal komplett: Produkt → Kundenbild → Warenkorb → Bestellung → Produktion."""
    user = make_user(db)
    product = make_product(db)
    product.images.append(ProductImage(file_path="storage/products/brett.jpg"))
    image = CustomerImage(user_id=user.id, product_id=product.id, original_path="storage/uploads/1.png")
    db.add(image)
    db.commit()

    db.add(CartItem(user_id=user.id, product_id=product.id, customer_image_id=image.id))
    order = Order(
        user_id=user.id, total_cent=2499,
        ship_first_name="Max", ship_last_name="Muster", ship_street="Hauptstraße 1",
        ship_postal_code="12345", ship_city="Berlin",
        bill_first_name="Max", bill_last_name="Muster", bill_street="Hauptstraße 1",
        bill_postal_code="12345", bill_city="Berlin",
    )
    order.items.append(OrderItem(product_id=product.id, customer_image_id=image.id, unit_price_cent=2499))
    db.add(order)
    db.commit()

    job = ProductionJob(order_id=order.id)
    job.files.append(ProductionFile(file_path="storage/production/1.svg", file_format="svg"))
    db.add(job)
    db.commit()

    assert order.status == "ordered"
    assert order.items[0].unit_price_cent == 2499
    assert image.status == "uploaded"
    assert job.files[0].sheet_number == 1


# Ungültige Eingaben

def test_email_must_be_unique(db):
    """Dieselbe E-Mail darf es nur einmal geben."""
    make_user(db)
    db.add(User(email="kunde@example.de", password_hash="hash"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_product_requires_price(db):
    """Ein Produkt ohne Preis wird abgelehnt."""
    db.add(Product(name="Ohne Preis", width_mm=10, height_mm=10))
    with pytest.raises(IntegrityError):
        db.commit()


# Grenzfälle

def test_only_one_production_job_per_order(db):
    """Zu einer Bestellung gibt es höchstens einen Produktionsauftrag."""
    user = make_user(db)
    order = Order(
        user_id=user.id, total_cent=0,
        ship_first_name="A", ship_last_name="B", ship_street="C 1", ship_postal_code="12345", ship_city="D",
        bill_first_name="A", bill_last_name="B", bill_street="C 1", bill_postal_code="12345", bill_city="D",
    )
    db.add(order)
    db.commit()
    db.add_all([ProductionJob(order_id=order.id), ProductionJob(order_id=order.id)])
    with pytest.raises(IntegrityError):
        db.commit()


def test_cart_item_without_customer_image(db):
    """Ein Warenkorb-Eintrag geht auch ohne Kundenbild (z. B. Produkt ohne Gravur)."""
    user = make_user(db)
    product = make_product(db)
    item = CartItem(user_id=user.id, product_id=product.id)
    db.add(item)
    db.commit()
    assert item.customer_image_id is None
    assert item.quantity == 1
