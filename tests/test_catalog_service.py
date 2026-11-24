"""Tests für app/catalog/service.py und den Demo-Seed (US01).

Normalfall, ungültige Eingaben und Grenzfälle. Die Fixture ``db`` aus conftest.py
liefert jedem Test eine leere Datenbank im Arbeitsspeicher.
"""

import pytest

from app.catalog import service
from app.catalog.models import Product
from app.catalog.service import InvalidProductTypeError, ProductNotFoundError
from scripts.seed_db import seed_demo_products


def make_product(db, name="Holzbrett", hidden=False, image_paths=("a.webp", "b.webp")):
    """Legt ein Produkt mit Standardwerten an, optional ausgeblendet."""
    product = service.create_product(
        db,
        name=name,
        description="Ein Brett. Mehr Text.",
        width_mm=200,
        height_mm=100,
        depth_mm=10,
        price_cent=1990,
        product_type=service.PRODUCT_TYPE_FINISHED,
        image_paths=image_paths,
    )
    if hidden:
        product.is_hidden = True
        db.commit()
    return product


# --------------------------------------------------------------------------- Normalfall


def test_create_product_stores_product_and_images_in_order(db):
    product = make_product(db, image_paths=["erstes.webp", "zweites.webp", "drittes.webp"])

    assert product.id is not None
    assert [image.file_path for image in product.images] == ["erstes.webp", "zweites.webp", "drittes.webp"]
    assert [image.sort_order for image in product.images] == [0, 1, 2]
    assert db.get(Product, product.id).price_cent == 1990


def test_list_visible_products_returns_only_visible_sorted_by_id(db):
    first = make_product(db, "Eins")
    make_product(db, "Versteckt", hidden=True)
    third = make_product(db, "Drei")

    result = service.list_visible_products(db)

    assert [p.id for p in result] == [first.id, third.id]


def test_get_visible_product_returns_product(db):
    product = make_product(db)

    assert service.get_visible_product(db, product.id).name == "Holzbrett"


def test_set_sold_out_true_then_false(db):
    product = make_product(db)

    assert service.set_sold_out(db, product.id, True).is_sold_out is True
    assert service.set_sold_out(db, product.id, False).is_sold_out is False


# --------------------------------------------------------------------------- Ungültig


def test_unknown_product_type_is_rejected(db):
    with pytest.raises(InvalidProductTypeError) as error:
        service.create_product(
            db,
            name="Unsinn",
            description="x",
            width_mm=1,
            height_mm=1,
            depth_mm=None,
            price_cent=100,
            product_type="gibt-es-nicht",
        )

    assert error.value.status_code == 422
    assert error.value.detail == "Unbekannte Produktart."
    assert db.query(Product).count() == 0  # nichts angelegt


def test_get_unknown_product_gives_404(db):
    with pytest.raises(ProductNotFoundError) as error:
        service.get_visible_product(db, 999)

    assert error.value.status_code == 404
    assert error.value.detail == "Dieses Produkt gibt es nicht."


def test_hidden_product_counts_as_not_found_for_public_get(db):
    product = make_product(db, hidden=True)

    with pytest.raises(ProductNotFoundError):
        service.get_visible_product(db, product.id)


def test_set_sold_out_works_on_hidden_product(db):
    product = make_product(db, hidden=True)

    assert service.set_sold_out(db, product.id, True).is_sold_out is True


def test_set_sold_out_unknown_id_gives_404(db):
    with pytest.raises(ProductNotFoundError):
        service.set_sold_out(db, 999, True)


def test_list_all_products_includes_hidden_sorted_by_id(db):
    first = make_product(db, "Eins")
    hidden = make_product(db, "Versteckt", hidden=True)
    third = make_product(db, "Drei")

    assert [p.id for p in service.list_all_products(db)] == [first.id, hidden.id, third.id]


def test_get_product_finds_hidden_product(db):
    product = make_product(db, hidden=True)

    assert service.get_product(db, product.id).is_hidden is True


def test_get_product_unknown_id_gives_404(db):
    with pytest.raises(ProductNotFoundError) as error:
        service.get_product(db, 999)

    assert error.value.status_code == 404


def test_set_hidden_true_then_false_keeps_product_in_database(db):
    product = make_product(db)

    assert service.set_hidden(db, product.id, True).is_hidden is True
    assert db.get(Product, product.id) is not None  # nur Flag, kein Löschen
    assert service.list_visible_products(db) == []

    assert service.set_hidden(db, product.id, False).is_hidden is False
    assert [p.id for p in service.list_visible_products(db)] == [product.id]


def test_set_hidden_unknown_id_gives_404(db):
    with pytest.raises(ProductNotFoundError):
        service.set_hidden(db, 999, True)


# --------------------------------------------------------------------------- Grenzfälle


def test_empty_database_gives_empty_list(db):
    assert service.list_visible_products(db) == []


def test_seed_demo_products_is_idempotent(db):
    assert seed_demo_products(db) == 4
    assert seed_demo_products(db) == 0

    products = service.list_visible_products(db)
    assert len(products) == 4
    assert [p.id for p in products[:3]] == [1, 2, 3]  # Fertigprodukte bekommen die IDs 1 bis 3

    gravurplatte = next(p for p in products if p.name == "Gravurplatte (Demo)")
    assert gravurplatte.product_type == service.PRODUCT_TYPE_CUSTOMER_IMAGE
    assert (gravurplatte.engraving_width_mm, gravurplatte.engraving_height_mm) == (80, 60)
    assert gravurplatte.description.startswith("Holzplatte für deine eigene Gravur. ")
