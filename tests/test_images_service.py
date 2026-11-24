"""Tests für app/images/service.py (US04 Task 1 und 2): Prüfung und Speichern von Kundenbildern.

Datenbank im Arbeitsspeicher (Fixture ``db`` aus conftest.py), Bilder im Test-Ordner.
"""

import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app import config
from app.accounts.models import User
from app.catalog.models import Product
from app.images import quality, service
from app.images.models import CustomerImage

PNG_HEADER = b"\x89PNG\r\n\x1a\n"
JPEG_HEADER = b"\xff\xd8\xff"
PNG = PNG_HEADER + b"\x00" * 50
JPEG = JPEG_HEADER + b"\x00" * 50


def image_bytes(width: int = 780, height: int = 580, fmt: str = "PNG", flat: bool = False) -> bytes:
    """Echtes Testbild (Schachbrett, scharf und kontrastreich). ``flat`` = einfarbig grau."""
    if flat:
        image = Image.new("L", (width, height), 128)
    else:
        y, x = np.indices((height, width))
        image = Image.fromarray((((x // 40 + y // 40) % 2) * 255).astype(np.uint8))
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


GOOD_PNG = image_bytes()
GOOD_JPEG = image_bytes(fmt="JPEG")


@pytest.fixture(autouse=True)
def local_uploads(tmp_path, monkeypatch):
    """Bilder landen im Test-Ordner, nie im echten uploads/."""
    monkeypatch.setattr(config, "UPLOAD_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def user(db):
    account = User(email="anna@example.de", password_hash="x", is_verified=True)
    db.add(account)
    db.commit()
    return account


@pytest.fixture
def other_user(db):
    account = User(email="ben@example.de", password_hash="x", is_verified=True)
    db.add(account)
    db.commit()
    return account


@pytest.fixture
def product(db):
    item = Product(
        name="Gravurplatte", width_mm=100, height_mm=80, price_cent=2990,
        engraving_width_mm=80, engraving_height_mm=60,
    )
    db.add(item)
    db.commit()
    return item


# --------------------------------------------------------------------------- validate_file (Task 2)


def test_png_and_jpeg_are_accepted():
    assert service.validate_file(PNG) == "png"
    assert service.validate_file(JPEG) == "jpg"


def test_exactly_5_mb_is_allowed():
    content = PNG_HEADER + b"\x00" * (service.MAX_BYTES - len(PNG_HEADER))
    assert len(content) == 5 * 1024 * 1024
    assert service.validate_file(content) == "png"


def test_one_byte_over_5_mb_is_rejected():
    content = PNG_HEADER + b"\x00" * (service.MAX_BYTES - len(PNG_HEADER) + 1)
    with pytest.raises(service.ImageValidationError) as error:
        service.validate_file(content)
    assert error.value.message == service.MSG_SIZE


@pytest.mark.parametrize(
    "content",
    [
        b"%PDF-1.4 ...",  # PDF
        b"RIFF\x00\x00\x00\x00WEBPVP8 ",  # WebP (beim Profilbild erlaubt, hier nicht)
        b"GIF89a....",  # GIF
        b"<svg xmlns='http://www.w3.org/2000/svg'/>",  # SVG
        b"\x89PN",  # abgeschnittener PNG-Anfang
    ],
)
def test_wrong_type_is_rejected(content):
    with pytest.raises(service.ImageValidationError) as error:
        service.validate_file(content)
    assert error.value.message == service.MSG_TYPE


def test_empty_file_is_rejected():
    with pytest.raises(service.ImageValidationError) as error:
        service.validate_file(b"")
    assert error.value.message == service.MSG_EMPTY


def test_error_has_field_format_for_frontend():
    with pytest.raises(service.ImageValidationError) as error:
        service.validate_file(b"")
    assert error.value.status_code == 422
    assert error.value.detail == [{"loc": ["body", "image"], "msg": service.MSG_EMPTY}]


# --------------------------------------------------------------------------- upload_image (Task 1)


def test_upload_saves_file_and_creates_entry(db, user, product, local_uploads):
    image = service.upload_image(db, user, product.id, GOOD_PNG).image

    assert image.id is not None
    assert image.user_id == user.id
    assert image.product_id == product.id
    assert image.status == "uploaded"
    assert image.original_path.startswith(f"customer-images/{user.id}-")
    assert image.original_path.endswith(".png")
    assert (Path(local_uploads) / image.original_path).read_bytes() == GOOD_PNG
    assert db.query(CustomerImage).count() == 1


def test_two_uploads_get_different_keys(db, user, product):
    first = service.upload_image(db, user, product.id, GOOD_PNG).image
    second = service.upload_image(db, user, product.id, GOOD_PNG).image
    assert first.original_path != second.original_path


def test_upload_for_unknown_product_is_rejected(db, user, local_uploads):
    with pytest.raises(service.ProductNotFoundError):
        service.upload_image(db, user, 999, GOOD_PNG)
    assert db.query(CustomerImage).count() == 0


def test_upload_for_hidden_product_is_rejected(db, user, product):
    product.is_hidden = True
    db.commit()
    with pytest.raises(service.ProductNotFoundError):
        service.upload_image(db, user, product.id, GOOD_PNG).image


def test_invalid_file_is_not_saved(db, user, product, local_uploads):
    with pytest.raises(service.ImageValidationError):
        service.upload_image(db, user, product.id, b"%PDF-1.4 ...")
    assert db.query(CustomerImage).count() == 0
    assert not (Path(local_uploads) / "customer-images").exists()


# --------------------------------------------------------------------------- get_own_image


def test_own_image_is_returned(db, user, product):
    image = service.upload_image(db, user, product.id, GOOD_JPEG).image
    assert service.get_own_image(db, user, image.id).id == image.id
    content, content_type = service.original_file(image)
    assert content == GOOD_JPEG
    assert content_type == "image/jpeg"


def test_foreign_image_is_not_found(db, user, other_user, product):
    image = service.upload_image(db, user, product.id, GOOD_PNG).image
    with pytest.raises(service.ImageNotFoundError):
        service.get_own_image(db, other_user, image.id)


def test_unknown_image_is_not_found(db, user):
    with pytest.raises(service.ImageNotFoundError):
        service.get_own_image(db, user, 12345)


def test_missing_file_in_storage_is_not_found(db, user, product, local_uploads):
    image = service.upload_image(db, user, product.id, GOOD_PNG).image
    (Path(local_uploads) / image.original_path).unlink()
    with pytest.raises(service.ImageNotFoundError):
        service.original_file(image)


# --------------------------------------------------------------------------- Qualitätsprüfung beim Upload (Task 3)


def test_good_image_has_no_warnings_and_needs_no_upscale(db, user, product):
    result = service.upload_image(db, user, product.id, GOOD_PNG)
    assert result.image.quality_warning is None
    assert result.quality.needs_upscale is False


def test_half_size_image_is_saved_and_needs_upscale(db, user, product):
    result = service.upload_image(db, user, product.id, image_bytes(390, 290))
    assert result.quality.needs_upscale is True
    assert result.image.status == "uploaded"


def test_too_small_image_is_rejected_and_not_saved(db, user, product, local_uploads):
    with pytest.raises(service.ImageValidationError) as error:
        service.upload_image(db, user, product.id, image_bytes(150, 100))
    assert error.value.message == "Das Bild ist zu klein für dieses Produkt. Es braucht mindestens 195 × 145 Pixel."
    assert db.query(CustomerImage).count() == 0
    assert not (Path(local_uploads) / "customer-images").exists()


def test_warnings_are_stored_separated(db, user, product):
    image = service.upload_image(db, user, product.id, image_bytes(flat=True)).image
    assert image.quality_warning == "; ".join([quality.WARNING_CONTRAST, quality.WARNING_SHARPNESS])


def test_broken_image_with_correct_header_is_rejected(db, user, product):
    with pytest.raises(service.ImageValidationError) as error:
        service.upload_image(db, user, product.id, PNG)  # PNG-Anfang, danach nur Nullen
    assert error.value.message == quality.MSG_UNREADABLE


def test_product_without_engraving_area_is_rejected_before_file_check(db, user, product):
    product.engraving_width_mm = None
    db.commit()
    with pytest.raises(service.ProductNotUploadableError) as error:
        service.upload_image(db, user, product.id, b"")  # leere Datei: Produkt wird zuerst geprüft
    assert error.value.status_code == 404
    assert error.value.detail == "Für dieses Produkt ist kein Bild-Upload möglich."
