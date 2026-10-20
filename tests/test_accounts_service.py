"""Tests für app/accounts: Prüfregeln, Registrieren, Code bestätigen, Anmelden, Sitzungen.

Die E-Mails werden nicht verschickt, sondern in der Liste ``sent_mails`` gesammelt.
So kann ein Test den Code aus der "E-Mail" lesen.
"""

import re
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app import config
from app.accounts import service
from app.accounts.models import User, UserSession, VerificationCode
from app.accounts.schemas import RegisterRequest
from app.accounts.validation import validate_registration

VALID_DATA = {
    "email": "Anna.Muster@Example.de",
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
    """Fängt alle E-Mails ab, statt sie zu verschicken. Liefert die Liste der Mails."""
    mails = []
    monkeypatch.setattr(service, "send_mail", lambda to, subject, body: mails.append({"to": to, "subject": subject, "body": body}))
    return mails


def code_from(mail) -> str:
    """Liest den 4-stelligen Code aus dem Text einer Bestätigungs-E-Mail."""
    return re.search(r"Bestätigungscode lautet: (\d{4})", mail["body"]).group(1)


def register(db, **changes) -> User:
    """Registriert ein Testkonto. Mit ``changes`` lassen sich einzelne Felder ändern."""
    return service.register_user(db, RegisterRequest(**{**VALID_DATA, **changes}))


def register_and_verify(db, sent_mails) -> User:
    """Registriert ein Testkonto und bestätigt es mit dem Code aus der E-Mail."""
    user = register(db)
    return service.verify_code(db, user.email, code_from(sent_mails[-1]))


# ------------------------------------------------------------------ Prüfregeln


def test_validation_accepts_valid_data():
    assert validate_registration(VALID_DATA) == {}


@pytest.mark.parametrize(
    ("field", "value", "expected_part"),
    [
        ("password", "abc1234", "mindestens 8 Zeichen"),  # Grenzfall: 7 Zeichen
        ("password", "abcdefgh", "Buchstaben und eine Ziffer"),  # keine Ziffer
        ("password", "12345678", "Buchstaben und eine Ziffer"),  # kein Buchstabe
        ("password", "a1" * 65, "höchstens 128"),
        ("email", "name@beispiel", "gültige E-Mail"),
        ("email", "na me@beispiel.de", "gültige E-Mail"),
        ("first_name", "A", "gültigen Namen"),
        ("last_name", "R2D2", "gültigen Namen"),
        ("street", "Musterstraße 12", "Hausnummer im Feld daneben"),  # Zahl in der Straße
        ("street", "Hauptstr.", "nur Buchstaben"),  # Sonderzeichen
        ("street", "Am  Ring", "nur Buchstaben"),  # doppeltes Leerzeichen
        ("street", "A", "nur Buchstaben"),  # zu kurz
        ("house_number", "a12", "Nur Ziffern"),
        ("house_number", "12ab", "Nur Ziffern"),
        ("house_number", "12-14", "Nur Ziffern"),
        ("house_number", "12345", "Nur Ziffern"),
        ("postal_code", "1234", "fünf Ziffern"),
        ("postal_code", "12a45", "fünf Ziffern"),
        ("city", "Berlin 10", "gültigen Ort"),
        ("city", "   ", "Bitte fülle dieses Feld aus"),
    ],
)
def test_validation_rejects_invalid_values(field, value, expected_part):
    errors = validate_registration({**VALID_DATA, field: value})
    assert list(errors) == [field]
    assert expected_part in errors[field]


@pytest.mark.parametrize("street", ["Am Ring", "Karl-Marx-Straße", "Schloßallee", "Lange Gasse"])
def test_validation_accepts_common_streets(street):
    assert validate_registration({**VALID_DATA, "street": street}) == {}


@pytest.mark.parametrize("house_number", ["1", "12", "12a", "1234B"])
def test_validation_accepts_common_house_numbers(house_number):
    assert validate_registration({**VALID_DATA, "house_number": house_number}) == {}


def test_validation_password_boundary_exactly_eight_characters():
    assert validate_registration({**VALID_DATA, "password": "abcd1234"}) == {}


def test_validation_accepts_umlauts():
    data = {**VALID_DATA, "first_name": "Jörg", "last_name": "Müller-Lüdenscheidt", "city": "Bad Homburg v. d. Höhe"}
    assert validate_registration(data) == {}


# ------------------------------------------------------------------ Passwort-Hash


def test_password_hash_is_not_plain_text_and_can_be_checked():
    stored = service.hash_password("geheim123")
    assert "geheim123" not in stored
    assert service.verify_password("geheim123", stored)
    assert not service.verify_password("geheim124", stored)


def test_same_password_gives_different_hashes():
    assert service.hash_password("geheim123") != service.hash_password("geheim123")


def test_verify_password_with_broken_hash_returns_false():
    assert not service.verify_password("geheim123", "kaputt")
    assert not service.verify_password("geheim123", "md5$1$2$3$zz$zz")


# ------------------------------------------------------------------ 1. Registrieren


def test_register_creates_unverified_user_with_address(db, sent_mails):
    user = register(db)

    assert user.email == "anna.muster@example.de"  # klein geschrieben
    assert user.role == "customer"
    assert user.is_verified is False
    assert user.password_hash != VALID_DATA["password"]
    assert service.verify_password(VALID_DATA["password"], user.password_hash)
    assert [(a.type, a.street, a.postal_code, a.city) for a in user.addresses] == [
        ("shipping", "Musterstraße 12", "12345", "Musterstadt")
    ]


def test_register_sends_mail_with_four_digit_code(db, sent_mails):
    register(db)

    assert len(sent_mails) == 1
    mail = sent_mails[0]
    assert mail["to"] == "anna.muster@example.de"
    assert mail["subject"] == "Dein LaserFlow-Bestätigungscode"
    assert mail["body"].startswith("Hallo Anna,")
    stored = db.scalar(select(VerificationCode))
    assert code_from(mail) == stored.code
    assert re.fullmatch(r"\d{4}", stored.code)


def test_register_trims_spaces(db, sent_mails):
    user = register(db, first_name="  Anna ", city=" Köln ", email="  anna@example.de ", street=" Am Ring ", house_number=" 3a ")
    assert user.first_name == "Anna"
    assert user.addresses[0].city == "Köln"
    assert user.addresses[0].street == "Am Ring 3a"  # Straße und Hausnummer zusammen gespeichert
    assert user.email == "anna@example.de"


def test_register_rejects_duplicate_email_case_insensitive(db, sent_mails):
    register(db)
    with pytest.raises(service.EmailAlreadyRegisteredError) as error:
        register(db, email="ANNA.MUSTER@example.de")
    assert error.value.status_code == 409
    assert db.query(User).count() == 1


def test_register_with_invalid_data_saves_nothing(db, sent_mails):
    with pytest.raises(service.RegistrationInvalidError) as error:
        register(db, password="kurz", postal_code="1")
    assert set(error.value.errors) == {"password", "postal_code"}
    assert error.value.status_code == 422
    assert {item["loc"][1] for item in error.value.detail} == {"password", "postal_code"}
    assert db.query(User).count() == 0
    assert sent_mails == []


# ------------------------------------------------------------------ 2. Code bestätigen


def test_correct_code_verifies_account(db, sent_mails):
    user = register(db)
    verified = service.verify_code(db, "Anna.Muster@example.de ", code_from(sent_mails[0]))

    assert verified.id == user.id
    assert verified.is_verified is True
    assert db.scalar(select(VerificationCode)).used_at is not None


def test_wrong_code_counts_attempts(db, sent_mails):
    register(db)
    real = code_from(sent_mails[0])
    wrong = "0000" if real != "0000" else "1111"

    with pytest.raises(service.CodeInvalidError) as error:
        service.verify_code(db, VALID_DATA["email"], wrong)
    assert error.value.status_code == 400
    assert "noch 4 Versuche" in error.value.detail
    assert db.scalar(select(VerificationCode)).failed_attempts == 1


def test_too_many_wrong_codes_lock_the_code(db, sent_mails):
    register(db)
    real = code_from(sent_mails[0])
    wrong = "0000" if real != "0000" else "1111"

    for _ in range(config.VERIFICATION_CODE_MAX_ATTEMPTS - 1):
        with pytest.raises(service.CodeInvalidError):
            service.verify_code(db, VALID_DATA["email"], wrong)
    # letzter erlaubter Fehlversuch → gesperrt
    with pytest.raises(service.TooManyAttemptsError):
        service.verify_code(db, VALID_DATA["email"], wrong)
    # auch der richtige Code hilft jetzt nicht mehr
    with pytest.raises(service.TooManyAttemptsError) as error:
        service.verify_code(db, VALID_DATA["email"], real)
    assert error.value.status_code == 429


def test_expired_code_is_rejected(db, sent_mails):
    register(db)
    code = db.scalar(select(VerificationCode))
    code.created_at = datetime.now() - timedelta(minutes=config.VERIFICATION_CODE_VALID_MINUTES + 1)
    db.commit()

    with pytest.raises(service.CodeExpiredError) as error:
        service.verify_code(db, VALID_DATA["email"], code.code)
    assert error.value.status_code == 410


def test_code_just_before_expiry_still_works(db, sent_mails):
    register(db)
    code = db.scalar(select(VerificationCode))
    code.created_at = datetime.now() - timedelta(minutes=config.VERIFICATION_CODE_VALID_MINUTES - 1)
    db.commit()
    assert service.verify_code(db, VALID_DATA["email"], code.code).is_verified


def test_resend_code_makes_old_code_invalid(db, sent_mails):
    register(db)
    old = code_from(sent_mails[0])
    service.resend_code(db, VALID_DATA["email"])
    new = code_from(sent_mails[1])

    if old != new:  # sehr selten zufällig gleich
        with pytest.raises(service.CodeInvalidError):
            service.verify_code(db, VALID_DATA["email"], old)
    assert service.verify_code(db, VALID_DATA["email"], new).is_verified


def test_resend_code_for_unknown_or_verified_email_sends_nothing(db, sent_mails):
    service.resend_code(db, "niemand@example.de")
    assert sent_mails == []

    register_and_verify(db, sent_mails)
    count = len(sent_mails)
    service.resend_code(db, VALID_DATA["email"])
    assert len(sent_mails) == count


def test_verify_already_verified_account(db, sent_mails):
    register_and_verify(db, sent_mails)
    with pytest.raises(service.AlreadyVerifiedError):
        service.verify_code(db, VALID_DATA["email"], "1234")


def test_verify_unknown_email_gives_same_error_as_wrong_code(db):
    with pytest.raises(service.CodeInvalidError) as error:
        service.verify_code(db, "niemand@example.de", "1234")
    assert error.value.detail == service.MSG_CODE_WRONG


def test_verify_with_strange_input_does_not_crash(db, sent_mails):
    register(db)
    with pytest.raises(service.CodeInvalidError):
        service.verify_code(db, VALID_DATA["email"], "é1€3")


# ------------------------------------------------------------------ 3. Anmelden


def test_login_after_verification(db, sent_mails):
    user = register_and_verify(db, sent_mails)
    assert service.authenticate(db, " ANNA.muster@example.de", VALID_DATA["password"]).id == user.id


def test_login_before_verification_is_refused(db, sent_mails):
    register(db)
    with pytest.raises(service.AccountNotVerifiedError) as error:
        service.authenticate(db, VALID_DATA["email"], VALID_DATA["password"])
    assert error.value.status_code == 403


@pytest.mark.parametrize(
    ("email", "password"),
    [
        (VALID_DATA["email"], "falsch123"),  # Passwort falsch
        ("niemand@example.de", VALID_DATA["password"]),  # E-Mail unbekannt
        (VALID_DATA["email"], ""),  # leeres Passwort
    ],
)
def test_login_with_wrong_data_gives_same_message(db, sent_mails, email, password):
    register_and_verify(db, sent_mails)
    with pytest.raises(service.InvalidCredentialsError) as error:
        service.authenticate(db, email, password)
    assert error.value.status_code == 401
    assert error.value.detail == "E-Mail-Adresse oder Passwort ist falsch."


def test_login_unverified_with_wrong_password_does_not_reveal_account(db, sent_mails):
    register(db)
    with pytest.raises(service.InvalidCredentialsError):
        service.authenticate(db, VALID_DATA["email"], "falsch123")


def test_deactivated_or_anonymized_account_cannot_log_in(db, sent_mails):
    user = register_and_verify(db, sent_mails)
    user.is_active = False
    db.commit()
    with pytest.raises(service.InvalidCredentialsError):
        service.authenticate(db, VALID_DATA["email"], VALID_DATA["password"])

    user.is_active = True
    user.anonymized_at = datetime.now()
    db.commit()
    with pytest.raises(service.InvalidCredentialsError):
        service.authenticate(db, VALID_DATA["email"], VALID_DATA["password"])


# ------------------------------------------------------------------ 4. Sitzungen


def test_session_create_read_delete(db, sent_mails):
    user = register_and_verify(db, sent_mails)
    token = service.create_session(db, user)

    assert len(token) >= 40
    assert service.get_user_by_session(db, token).id == user.id

    service.delete_session(db, token)
    assert service.get_user_by_session(db, token) is None


def test_unknown_or_missing_token_means_not_logged_in(db):
    assert service.get_user_by_session(db, None) is None
    assert service.get_user_by_session(db, "") is None
    assert service.get_user_by_session(db, "gibt-es-nicht") is None
    service.delete_session(db, "gibt-es-nicht")  # darf keinen Fehler werfen


def test_expired_session_is_removed(db, sent_mails):
    user = register_and_verify(db, sent_mails)
    token = service.create_session(db, user)
    session = db.scalar(select(UserSession))
    session.expires_at = datetime.now() - timedelta(seconds=1)
    db.commit()

    assert service.get_user_by_session(db, token) is None
    assert db.query(UserSession).count() == 0


def test_session_of_deactivated_user_is_invalid(db, sent_mails):
    user = register_and_verify(db, sent_mails)
    token = service.create_session(db, user)
    user.is_active = False
    db.commit()
    assert service.get_user_by_session(db, token) is None
