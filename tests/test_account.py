"""Tests für "Mein Konto" (US10): app/accounts/account_service.py und account_router.py.

Profilbilder landen in einem Test-Ordner (tmp_path), nie im echten uploads/.
E-Mails werden abgefangen und in ``sent_mails`` gesammelt.
"""

import re

import boto3
import pytest
from botocore.stub import Stubber
from sqlalchemy import select

from app import config, storage
from app.accounts import account_service, service
from app.accounts.models import Address, User, UserSession
from app.accounts.schemas import RegisterRequest
from app.catalog.models import Product
from app.images.models import CustomerImage
from app.orders.models import CartItem, Order, OrderItem

PASSWORD = "geheim123"
REGISTER_DATA = {
    "email": "anna@example.de",
    "password": PASSWORD,
    "first_name": "Anna",
    "last_name": "Muster",
    "street": "Musterstraße",
    "house_number": "12",
    "postal_code": "12345",
    "city": "Musterstadt",
}
PROFILE = {
    "first_name": "Anne",
    "last_name": "Neumann",
    "street": "Am Ring",
    "house_number": "3a",
    "postal_code": "54321",
    "city": "Köln",
}

# Kleinste gültige Bild-Anfänge ("Magic Bytes") + etwas Inhalt
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 50
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 50


@pytest.fixture
def sent_mails(monkeypatch):
    """Fängt alle E-Mails ab (aus service.py und account_service.py)."""
    mails = []

    def fake_send(to, subject, body):
        mails.append({"to": to, "subject": subject, "body": body})

    monkeypatch.setattr(service, "send_mail", fake_send)
    monkeypatch.setattr(account_service, "send_mail", fake_send)
    return mails


@pytest.fixture(autouse=True)
def upload_dir(tmp_path, monkeypatch):
    """Profilbilder in einen Test-Ordner speichern."""
    monkeypatch.setattr(config, "UPLOAD_DIR", str(tmp_path))
    return tmp_path


def code_from(mail) -> str:
    return re.search(r"Bestätigungscode lautet: (\d{4})", mail["body"]).group(1)


@pytest.fixture
def user(db, sent_mails) -> User:
    """Ein registriertes und bestätigtes Konto."""
    new_user = service.register_user(db, RegisterRequest(**REGISTER_DATA))
    return service.verify_code(db, new_user.email, code_from(sent_mails[-1]))


# ------------------------------------------------------------------ Ansehen


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ("Musterstraße 12", ("Musterstraße", "12")),
        ("Am Ring 3a", ("Am Ring", "3a")),
        ("Karl-Marx-Straße 1234B", ("Karl-Marx-Straße", "1234B")),
        ("Ohne Nummer", ("Ohne Nummer", "")),  # alte Daten ohne Hausnummer
    ],
)
def test_split_street(stored, expected):
    assert account_service.split_street(stored) == expected


def test_get_profile(user):
    profile = account_service.get_profile(user)
    assert profile["email"] == "anna@example.de"
    assert (profile["street"], profile["house_number"]) == ("Musterstraße", "12")
    assert (profile["postal_code"], profile["city"]) == ("12345", "Musterstadt")
    assert profile["pending_email"] is None
    assert profile["avatar_path"] is None


# ------------------------------------------------------------------ Daten ändern


def test_update_profile(db, user):
    account_service.update_profile(db, user, PROFILE)
    db.refresh(user)
    assert (user.first_name, user.last_name) == ("Anne", "Neumann")
    address = db.scalar(select(Address).where(Address.user_id == user.id))
    assert (address.street, address.postal_code, address.city) == ("Am Ring 3a", "54321", "Köln")
    assert db.query(Address).count() == 1  # geändert, nicht zusätzlich angelegt


@pytest.mark.parametrize(
    ("field", "value"),
    [("street", "Am Ring 3"), ("house_number", "3-5"), ("postal_code", "123"), ("first_name", ""), ("city", "Köln 1")],
)
def test_update_profile_invalid_changes_nothing(db, user, field, value):
    with pytest.raises(service.FieldValidationError) as error:
        account_service.update_profile(db, user, {**PROFILE, field: value})
    assert list(error.value.errors) == [field]
    db.refresh(user)
    assert user.first_name == "Anna"


# ------------------------------------------------------------------ Passwort


def test_change_password_keeps_current_session_only(db, user):
    current = service.create_session(db, user)
    other = service.create_session(db, user)

    account_service.change_password(db, user, PASSWORD, "neuesPasswort1", keep_token=current)

    assert service.verify_password("neuesPasswort1", user.password_hash)
    assert service.get_user_by_session(db, current) is not None
    assert service.get_user_by_session(db, other) is None
    assert service.authenticate(db, user.email, "neuesPasswort1").id == user.id


@pytest.mark.parametrize(
    ("current", "new", "field", "part"),
    [
        ("falsch123", "neuesPasswort1", "current_password", "falsch"),
        (PASSWORD, "kurz1", "new_password", "mindestens 8"),
        (PASSWORD, "nurbuchstaben", "new_password", "Ziffer"),
        (PASSWORD, PASSWORD, "new_password", "unterscheiden"),
    ],
)
def test_change_password_errors(db, user, current, new, field, part):
    with pytest.raises(service.FieldValidationError) as error:
        account_service.change_password(db, user, current, new, keep_token=None)
    assert part in error.value.errors[field]
    assert service.verify_password(PASSWORD, user.password_hash)


# ------------------------------------------------------------------ E-Mail ändern


def test_email_change_full_flow(db, user, sent_mails):
    pending = account_service.request_email_change(db, user, " Neu@Example.de ", PASSWORD)
    assert pending == "neu@example.de"
    assert user.email == "anna@example.de"  # gilt erst nach dem Code
    assert sent_mails[-1]["to"] == "neu@example.de"
    assert "E-Mail-Adresse bei LaserFlow ändern" in sent_mails[-1]["body"]

    account_service.confirm_email_change(db, user, code_from(sent_mails[-1]))
    assert user.email == "neu@example.de"
    assert user.pending_email is None
    # Hinweis an die alte Adresse
    assert sent_mails[-1]["to"] == "anna@example.de"
    # Anmelden geht jetzt mit der neuen Adresse
    assert service.authenticate(db, "neu@example.de", PASSWORD).id == user.id


@pytest.mark.parametrize(
    ("new_email", "password", "field"),
    [
        ("neu@example.de", "falsch123", "password"),
        ("keine-mail", PASSWORD, "new_email"),
        ("ANNA@example.de", PASSWORD, "new_email"),  # gleiche Adresse
        ("", PASSWORD, "new_email"),
    ],
)
def test_email_change_request_errors(db, user, new_email, password, field):
    with pytest.raises(service.FieldValidationError) as error:
        account_service.request_email_change(db, user, new_email, password)
    assert list(error.value.errors) == [field]
    assert user.pending_email is None


def test_email_change_to_taken_address(db, user, sent_mails):
    service.register_user(db, RegisterRequest(**{**REGISTER_DATA, "email": "belegt@example.de"}))
    with pytest.raises(service.FieldValidationError) as error:
        account_service.request_email_change(db, user, "belegt@example.de", PASSWORD)
    assert error.value.errors["new_email"] == service.MSG_EMAIL_TAKEN


def test_email_change_wrong_code_and_cancel(db, user, sent_mails):
    account_service.request_email_change(db, user, "neu@example.de", PASSWORD)
    wrong = "0000" if code_from(sent_mails[-1]) != "0000" else "1111"
    with pytest.raises(service.CodeInvalidError):
        account_service.confirm_email_change(db, user, wrong)

    account_service.cancel_email_change(db, user)
    assert user.pending_email is None
    with pytest.raises(account_service.NoPendingEmailError):
        account_service.confirm_email_change(db, user, "1234")
    assert user.email == "anna@example.de"


def test_email_change_resend_code(db, user, sent_mails):
    with pytest.raises(account_service.NoPendingEmailError):
        account_service.resend_email_change_code(db, user)
    account_service.request_email_change(db, user, "neu@example.de", PASSWORD)
    account_service.resend_email_change_code(db, user)
    assert sent_mails[-1]["to"] == "neu@example.de"
    account_service.confirm_email_change(db, user, code_from(sent_mails[-1]))
    assert user.email == "neu@example.de"


# ------------------------------------------------------------------ Profilbild


@pytest.mark.parametrize(
    ("content", "extension", "content_type"),
    [(PNG, "png", "image/png"), (JPG, "jpg", "image/jpeg"), (WEBP, "webp", "image/webp")],
)
def test_save_avatar(db, user, upload_dir, content, extension, content_type):
    account_service.save_avatar(db, user, content)
    # In der Datenbank steht nur der Schlüssel, nicht der volle Pfad
    assert user.avatar_path.startswith(f"avatars/{user.id}-")
    assert user.avatar_path.endswith(f".{extension}")
    assert (upload_dir / user.avatar_path).read_bytes() == content  # lokal liegt die Datei unter UPLOAD_DIR
    assert account_service.avatar_image(user) == (content, content_type)


def test_new_avatar_replaces_old_file(db, user, upload_dir):
    account_service.save_avatar(db, user, PNG)
    old = upload_dir / user.avatar_path
    account_service.save_avatar(db, user, JPG)
    assert not old.exists()
    assert user.avatar_path.endswith(".jpg")
    assert account_service.avatar_image(user)[1] == "image/jpeg"


def test_avatar_image_is_none_when_file_is_missing(db, user):
    user.avatar_path = "avatars/1-fehlt.png"  # Eintrag ohne Datei
    db.commit()
    assert account_service.avatar_image(user) is None


@pytest.mark.parametrize(
    ("content", "part"),
    [(b"", "leer"), (b"GIF89a" + b"\x00" * 20, "JPG, PNG oder WebP"), (b"%PDF-1.4", "JPG, PNG oder WebP")],
)
def test_save_avatar_rejects_bad_files(db, user, content, part):
    with pytest.raises(service.FieldValidationError) as error:
        account_service.save_avatar(db, user, content)
    assert part in error.value.errors["avatar"]
    assert user.avatar_path is None


def test_save_avatar_size_limit(db, user, monkeypatch):
    monkeypatch.setattr(config, "AVATAR_MAX_BYTES", 100)
    exactly_100 = PNG + b"\x00" * (100 - len(PNG))
    account_service.save_avatar(db, user, exactly_100)  # Grenzfall: genau die Grenze ist erlaubt
    with pytest.raises(service.FieldValidationError) as error:
        account_service.save_avatar(db, user, exactly_100 + b"\x00")
    assert "höchstens" in error.value.errors["avatar"]


def test_remove_avatar(db, user, upload_dir):
    account_service.save_avatar(db, user, PNG)
    path = upload_dir / user.avatar_path
    account_service.remove_avatar(db, user)
    assert user.avatar_path is None
    assert not path.exists()
    assert account_service.avatar_image(user) is None


# ------------------------------------------------------------------ Konto löschen (Akzeptanzkriterien US10)


def make_order(db, user, status="ordered", with_image=False) -> Order:
    """Legt eine Bestellung mit einer Position an (Adresse wie beim Bestellen kopiert)."""
    product = Product(name="Holzbrett", width_mm=300, height_mm=200, price_cent=2499)
    db.add(product)
    db.flush()
    image = None
    if with_image:
        image = CustomerImage(user_id=user.id, product_id=product.id, original_path="uploads/bild.png")
        db.add(image)
        db.flush()
    address = dict(ship_first_name="Anna", ship_last_name="Muster", ship_street="Musterstraße 12",
                   ship_postal_code="12345", ship_city="Musterstadt", bill_first_name="Anna",
                   bill_last_name="Muster", bill_street="Musterstraße 12", bill_postal_code="12345",
                   bill_city="Musterstadt")
    order = Order(user_id=user.id, status=status, total_cent=2499, **address)
    order.items.append(OrderItem(product_id=product.id, unit_price_cent=2499,
                                 customer_image_id=image.id if image else None))
    db.add(order)
    db.commit()
    return order


def assert_anonymized(db, user):
    """Persönliche Daten weg, Konto-Zeile bleibt."""
    db.refresh(user)
    assert user.is_active is False
    assert user.anonymized_at is not None
    assert user.first_name is None and user.last_name is None
    assert user.email == f"geloescht-{user.id}@anonymisiert.invalid"
    assert user.avatar_path is None
    assert db.query(Address).filter_by(user_id=user.id).count() == 0
    assert db.query(UserSession).filter_by(user_id=user.id).count() == 0


def test_delete_without_orders_logs_out_and_anonymizes_immediately(db, user, upload_dir):
    account_service.save_avatar(db, user, PNG)
    avatar = upload_dir / user.avatar_path
    token = service.create_session(db, user)

    assert account_service.delete_account(db, user, PASSWORD) is True

    assert service.get_user_by_session(db, token) is None  # abgemeldet
    assert_anonymized(db, user)
    assert not avatar.exists()  # Profilbild-Datei gelöscht
    with pytest.raises(service.InvalidCredentialsError):  # keine erneute Anmeldung
        service.authenticate(db, "anna@example.de", PASSWORD)
    assert db.get(User, user.id) is not None  # Zeile bleibt (für Belege)


def test_email_is_free_again_after_anonymization(db, user, sent_mails):
    account_service.delete_account(db, user, PASSWORD)
    new_user = service.register_user(db, RegisterRequest(**REGISTER_DATA))
    assert new_user.id != user.id


def test_delete_with_running_order_keeps_data_until_shipped(db, user):
    order = make_order(db, user, status="in_production")

    assert account_service.delete_account(db, user, PASSWORD) is False

    # sofort: abgemeldet und deaktiviert, aber noch nicht anonymisiert
    db.refresh(user)
    assert user.is_active is False
    assert user.anonymized_at is None
    assert user.first_name == "Anna"
    with pytest.raises(service.InvalidCredentialsError):
        service.authenticate(db, "anna@example.de", PASSWORD)
    # die Bestellung läuft normal weiter
    db.refresh(order)
    assert order.status == "in_production"

    # Bestellung wird versendet → jetzt anonymisieren
    order.status = "shipped"
    db.commit()
    assert account_service.anonymize_if_possible(db, user) is True
    assert_anonymized(db, user)

    # Bestell- und Rechnungsbeleg bleibt vollständig erhalten
    db.refresh(order)
    assert (order.ship_last_name, order.bill_street, order.total_cent) == ("Muster", "Musterstraße 12", 2499)
    assert len(order.items) == 1


@pytest.mark.parametrize("status", ["ordered", "paid", "in_production"])
def test_running_statuses_block_anonymization(db, user, status):
    make_order(db, user, status=status)
    account_service.delete_account(db, user, PASSWORD)
    assert account_service.anonymize_if_possible(db, user) is False


@pytest.mark.parametrize("status", ["shipped", "cancelled"])
def test_finished_orders_do_not_block(db, user, status):
    make_order(db, user, status=status)
    assert account_service.delete_account(db, user, PASSWORD) is True
    assert_anonymized(db, user)


def test_anonymize_pending_accounts_at_startup(db, user):
    order = make_order(db, user, status="paid")
    account_service.delete_account(db, user, PASSWORD)
    assert account_service.anonymize_pending_accounts(db) == 0  # läuft noch

    order.status = "shipped"
    db.commit()
    assert account_service.anonymize_pending_accounts(db) == 1
    assert_anonymized(db, user)
    assert account_service.anonymize_pending_accounts(db) == 0  # nicht doppelt


def test_active_account_is_never_anonymized(db, user):
    assert account_service.anonymize_if_possible(db, user) is False
    assert user.first_name == "Anna"


def test_customer_images_in_orders_are_kept(db, user, upload_dir):
    make_order(db, user, status="shipped", with_image=True)
    key = "customer-images/1-lose.png"  # Schlüssel im Bildspeicher, wie beim Upload (US04)
    storage.save_file(key, PNG)
    loose = CustomerImage(user_id=user.id, product_id=1, original_path=key)
    db.add(loose)
    db.add(CartItem(user_id=user.id, product_id=1))
    db.commit()

    account_service.delete_account(db, user, PASSWORD)

    remaining = db.query(CustomerImage).filter_by(user_id=user.id).all()
    assert len(remaining) == 1  # nur das Bild aus der Bestellung
    assert storage.read_file(key) is None
    assert not (upload_dir / key).exists()
    assert db.query(CartItem).filter_by(user_id=user.id).count() == 0


def test_customer_images_are_deleted_in_object_storage(db, user, monkeypatch):
    """Mit Bucket (Fake, kein Netz): Beim Anonymisieren geht ein Löschauftrag für das Kundenbild raus."""
    key = "customer-images/1-lose.png"
    db.add(CustomerImage(user_id=user.id, product_id=1, original_path=key))
    db.commit()
    client = boto3.client("s3", region_name="eu-central-1", endpoint_url="https://example.invalid",
                          aws_access_key_id="x", aws_secret_access_key="y")
    monkeypatch.setattr(config, "STORAGE_BUCKET", "testbucket")
    storage.set_client(client)
    try:
        with Stubber(client) as stubber:
            stubber.add_response("delete_object", {}, {"Bucket": "testbucket", "Key": key})
            account_service.delete_account(db, user, PASSWORD)
            stubber.assert_no_pending_responses()
    finally:
        storage.set_client(None)
    assert db.query(CustomerImage).filter_by(user_id=user.id).count() == 0


def test_delete_account_needs_correct_password(db, user):
    with pytest.raises(service.FieldValidationError) as error:
        account_service.delete_account(db, user, "falsch123")
    assert "password" in error.value.errors
    assert user.is_active is True
