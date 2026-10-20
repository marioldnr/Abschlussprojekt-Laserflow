"""Logik für "Mein Konto" (US10): Daten ansehen und ändern, E-Mail und Passwort ändern,
Profilbild, Konto löschen und anonymisieren.

Alle Funktionen bekommen das angemeldete Konto (``user``) vom Router. Wer angemeldet ist,
prüft der Router über ``dependencies.get_current_user``.

Geht etwas schief, werfen die Funktionen einen ``service.AccountError`` (siehe service.py),
meist einen ``FieldValidationError`` mit Meldung pro Formularfeld.
"""

import re
import secrets
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app import config
from app.accounts import service
from app.accounts.models import Address, User, UserSession, VerificationCode
from app.images.models import CustomerImage
from app.orders.models import CartItem, Order, OrderItem
from app.accounts.validation import PROFILE_RULES, check_email, check_password, validate_fields
from app.mail import send_mail

MSG_WRONG_PASSWORD = "Das Passwort ist falsch."
MSG_SAME_PASSWORD = "Das neue Passwort muss sich vom aktuellen unterscheiden."
MSG_SAME_EMAIL = "Das ist bereits deine E-Mail-Adresse."
MSG_NO_PENDING_EMAIL = "Es gibt keine offene Änderung der E-Mail-Adresse."
MSG_AVATAR_TYPE = "Bitte wähle ein Bild im Format JPG, PNG oder WebP."
MSG_AVATAR_SIZE = f"Das Bild darf höchstens {config.AVATAR_MAX_BYTES // (1024 * 1024)} MB groß sein."
MSG_AVATAR_EMPTY = "Die Datei ist leer."


class NoPendingEmailError(service.AccountError):
    """Es wurde keine neue E-Mail-Adresse angefordert (409)."""

    status_code = 409


# --------------------------------------------------------------------------- Ansehen


def split_street(stored: str) -> tuple[str, str]:
    """Teilt "Musterstraße 12" wieder in Straße und Hausnummer.

    In der Datenbank stehen beide zusammen (CLAUDE.md, Abschnitt Datenbank). Weil beim
    Speichern geprüft wird, dass die Straße keine Ziffern enthält, ist das letzte Wort
    immer die Hausnummer.

    Returns:
        (Straße, Hausnummer). Ohne erkennbare Hausnummer: (alles, "").
    """
    parts = stored.strip().rsplit(" ", 1)
    if len(parts) == 2 and re.fullmatch(r"[0-9]{1,4}[a-zA-Z]?", parts[1]):
        return parts[0], parts[1]
    return stored.strip(), ""


def _shipping_address(user: User) -> Address | None:
    """Die Lieferadresse des Kontos (bei der Registrierung angelegt)."""
    return next((address for address in user.addresses if address.type == "shipping"), None)


def get_profile(user: User) -> dict:
    """Alle Daten für die Seite "Mein Konto".

    Returns:
        Dictionary passend zu ``schemas.ProfileResponse``.
    """
    address = _shipping_address(user)
    street, house_number = split_street(address.street) if address else ("", "")
    return {
        "email": user.email,
        "pending_email": user.pending_email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "street": street,
        "house_number": house_number,
        "postal_code": address.postal_code if address else "",
        "city": address.city if address else "",
        "avatar_path": user.avatar_path,
        "created_at": user.created_at,
    }


# --------------------------------------------------------------------------- Daten ändern


def update_profile(db: Session, user: User, data: dict[str, str]) -> User:
    """Ändert Name und Lieferadresse.

    Es gelten dieselben Regeln wie bei der Registrierung (validation.PROFILE_RULES).
    Alte Bestellungen ändern sich dadurch nicht, weil dort die Adresse kopiert ist.

    Raises:
        FieldValidationError: mindestens ein Feld ist ungültig.
    """
    errors = validate_fields(data, PROFILE_RULES)
    if errors:
        raise service.FieldValidationError(errors)

    user.first_name = data["first_name"].strip()
    user.last_name = data["last_name"].strip()
    address = _shipping_address(user)
    if address is None:
        address = Address(type="shipping", street="", postal_code="", city="")
        user.addresses.append(address)
    address.street = f"{data['street'].strip()} {data['house_number'].strip()}"
    address.postal_code = data["postal_code"].strip()
    address.city = data["city"].strip()
    db.commit()
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str, keep_token: str | None) -> None:
    """Ändert das Passwort.

    Danach werden alle anderen Sitzungen beendet (z. B. auf einem fremden Rechner),
    nur die aktuelle (``keep_token``) bleibt angemeldet.

    Raises:
        FieldValidationError: aktuelles Passwort falsch, neues zu schwach oder gleich dem alten.
    """
    if not service.verify_password(current_password, user.password_hash):
        raise service.FieldValidationError({"current_password": MSG_WRONG_PASSWORD})
    message = check_password(new_password)
    if message is None and service.verify_password(new_password, user.password_hash):
        message = MSG_SAME_PASSWORD
    if message:
        raise service.FieldValidationError({"new_password": message})

    user.password_hash = service.hash_password(new_password)
    for session in db.scalars(select(UserSession).where(UserSession.user_id == user.id)):
        if session.token != keep_token:
            db.delete(session)
    db.commit()


# --------------------------------------------------------------------------- E-Mail ändern


def _email_change_mail_text(first_name: str | None, code: str) -> str:
    """Standardtext der E-Mail an die NEUE Adresse."""
    greeting = f"Hallo {first_name}," if first_name else "Hallo,"
    return (
        f"{greeting}\n\n"
        + "du möchtest deine E-Mail-Adresse bei LaserFlow ändern.\n\n"
        + f"Dein Bestätigungscode lautet: {code}\n\n"
        + f"Der Code ist {config.VERIFICATION_CODE_VALID_MINUTES} Minuten gültig. "
        + "Falls du das nicht warst, kannst du diese E-Mail ignorieren.\n\n"
        + "Dein LaserFlow-Team"
    )


def _email_taken(db: Session, email: str, user: User) -> bool:
    """Gehört die Adresse schon einem anderen Konto (auch als offene Änderung)?"""
    other = db.scalar(
        select(User).where(User.id != user.id, or_(User.email == email, User.pending_email == email))
    )
    return other is not None


def request_email_change(db: Session, user: User, new_email: str, password: str) -> str:
    """Startet die Änderung der E-Mail: Code an die neue Adresse schicken.

    Bis der Code bestätigt ist, gilt weiter die alte Adresse (auch zum Anmelden).

    Returns:
        die neue (noch nicht bestätigte) Adresse.

    Raises:
        FieldValidationError: Passwort falsch, Adresse ungültig, gleich oder schon vergeben.
    """
    if not service.verify_password(password, user.password_hash):
        raise service.FieldValidationError({"password": MSG_WRONG_PASSWORD})
    email = service.normalize_email(new_email)
    message = check_email(email) if email else "Bitte fülle dieses Feld aus."
    if message is None and email == user.email:
        message = MSG_SAME_EMAIL
    if message is None and _email_taken(db, email, user):
        message = service.MSG_EMAIL_TAKEN
    if message:
        raise service.FieldValidationError({"new_email": message})

    user.pending_email = email
    db.commit()
    service.create_and_send_code(db, user, to=email, mail_text=_email_change_mail_text)
    return email


def resend_email_change_code(db: Session, user: User) -> None:
    """Schickt einen neuen Code an die neue Adresse. Der alte Code gilt dann nicht mehr.

    Raises:
        NoPendingEmailError: es gibt keine offene Änderung.
    """
    if not user.pending_email:
        raise NoPendingEmailError(MSG_NO_PENDING_EMAIL)
    service.create_and_send_code(db, user, to=user.pending_email, mail_text=_email_change_mail_text)


def confirm_email_change(db: Session, user: User, code: str) -> User:
    """Bestätigt die neue E-Mail mit dem Code. Danach gilt nur noch die neue Adresse.

    Die alte Adresse bekommt einen Hinweis, damit ein Fremdzugriff auffällt.

    Raises:
        NoPendingEmailError: es gibt keine offene Änderung.
        CodeInvalidError, CodeExpiredError, TooManyAttemptsError: siehe service.check_and_use_code.
        EmailAlreadyRegisteredError: die Adresse wurde inzwischen von jemand anderem registriert.
    """
    if not user.pending_email:
        raise NoPendingEmailError(MSG_NO_PENDING_EMAIL)
    service.check_and_use_code(db, user, code)
    if db.scalar(select(User).where(User.id != user.id, User.email == user.pending_email)) is not None:
        user.pending_email = None
        db.commit()
        raise service.EmailAlreadyRegisteredError(service.MSG_EMAIL_TAKEN)

    old_email = user.email
    user.email = user.pending_email
    user.pending_email = None
    db.commit()
    send_mail(
        old_email,
        "Deine LaserFlow-E-Mail-Adresse wurde geändert",
        f"Hallo,\n\ndie E-Mail-Adresse deines LaserFlow-Kontos wurde auf {user.email} geändert.\n"
        "Falls du das nicht warst, melde dich bitte bei uns.\n\nDein LaserFlow-Team",
    )
    return user


def cancel_email_change(db: Session, user: User) -> None:
    """Bricht eine offene E-Mail-Änderung ab. Die alte Adresse bleibt."""
    user.pending_email = None
    db.commit()


# --------------------------------------------------------------------------- Profilbild

# Bildformate, erkannt an den ersten Bytes der Datei ("Magic Bytes"), nicht am Dateinamen.
# Der Dateiname oder der Content-Type lassen sich leicht fälschen, der Dateiinhalt nicht so einfach.
def _detect_image_type(content: bytes) -> str | None:
    """Liefert "jpg", "png" oder "webp", wenn der Inhalt so ein Bild ist, sonst None."""
    if content.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    return None


def _avatar_dir() -> Path:
    return Path(config.UPLOAD_DIR) / "avatars"


def _delete_file(path: str | None) -> None:
    """Löscht eine hochgeladene Datei, falls es sie gibt."""
    if path:
        Path(path).unlink(missing_ok=True)


def save_avatar(db: Session, user: User, content: bytes) -> User:
    """Speichert ein neues Profilbild und ersetzt das alte.

    Das Bild wird nicht verändert. Rund und quadratisch zugeschnitten wird es nur bei der
    Anzeige (CSS ``object-fit: cover``), dafür braucht es keine Bildbibliothek.
    Der Dateiname enthält einen Zufallsteil, damit der Browser nach einem Wechsel
    nicht das alte Bild aus dem Zwischenspeicher zeigt.

    Raises:
        FieldValidationError: Datei leer, zu groß oder kein JPG/PNG/WebP (Feld "avatar").
    """
    if not content:
        raise service.FieldValidationError({"avatar": MSG_AVATAR_EMPTY})
    if len(content) > config.AVATAR_MAX_BYTES:
        raise service.FieldValidationError({"avatar": MSG_AVATAR_SIZE})
    extension = _detect_image_type(content)
    if extension is None:
        raise service.FieldValidationError({"avatar": MSG_AVATAR_TYPE})

    folder = _avatar_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{user.id}-{secrets.token_hex(8)}.{extension}"
    path.write_bytes(content)

    old_path = user.avatar_path
    user.avatar_path = str(path)
    db.commit()
    _delete_file(old_path)
    return user


def remove_avatar(db: Session, user: User) -> None:
    """Entfernt das Profilbild. Danach zeigt das Icon wieder das Standard-Symbol."""
    old_path = user.avatar_path
    user.avatar_path = None
    db.commit()
    _delete_file(old_path)


def avatar_file(user: User) -> Path | None:
    """Pfad zur Bilddatei, wenn es ein Profilbild gibt und die Datei existiert."""
    if not user.avatar_path:
        return None
    path = Path(user.avatar_path)
    return path if path.is_file() else None


# --------------------------------------------------------------------------- Konto löschen

# Bestellungen in diesen Zuständen laufen noch (siehe Docstring von orders.models.Order).
# Erst wenn keine Bestellung mehr so einen Status hat, wird anonymisiert.
OPEN_ORDER_STATUSES = ("ordered", "paid", "in_production")


def delete_account(db: Session, user: User, password: str) -> bool:
    """Löscht das Konto aus Sicht des Kunden (US10, Use Case "Konto löschen").

    Akzeptanzkriterien:
        - Nach dem Löschen ist der Kunde abgemeldet und das Konto deaktiviert,
          eine erneute Anmeldung ist nicht möglich.
        - Das geht auch bei laufenden Bestellungen; diese werden normal weiterbearbeitet
          und versendet (die Bestellungen werden hier nicht angefasst).
        - Bestell- und Rechnungsbelege bleiben gespeichert, die übrigen persönlichen Daten
          werden anonymisiert, sobald alle laufenden Bestellungen versendet sind.
          Gibt es keine laufende Bestellung, passiert das sofort.

    Returns:
        True, wenn sofort anonymisiert wurde; False, wenn noch Bestellungen laufen
        (dann übernimmt das später anonymize_if_possible()).

    Raises:
        FieldValidationError: Passwort falsch (Feld "password"), so wird die Löschung bestätigt.
    """
    if not service.verify_password(password, user.password_hash):
        raise service.FieldValidationError({"password": MSG_WRONG_PASSWORD})
    user.is_active = False
    user.pending_email = None
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.commit()
    return anonymize_if_possible(db, user)


def has_open_orders(db: Session, user: User) -> bool:
    """Hat das Konto noch Bestellungen, die nicht versendet (oder storniert) sind?"""
    open_order = db.scalar(
        select(Order.id).where(Order.user_id == user.id, Order.status.in_(OPEN_ORDER_STATUSES)).limit(1)
    )
    return open_order is not None


def anonymize_if_possible(db: Session, user: User) -> bool:
    """Anonymisiert ein gelöschtes Konto, sobald keine Bestellung mehr läuft.

    Wird aufgerufen:
        - direkt beim Löschen (delete_account),
        - beim Start der App für alle gelöschten Konten (anonymize_pending_accounts),
        - WICHTIG für die Story "Bestellstatus ändern": nachdem eine Bestellung auf
          "shipped" gesetzt wurde, mit dem Kunden der Bestellung aufrufen.

    Returns:
        True, wenn jetzt anonymisiert wurde. False, wenn das Konto noch aktiv ist,
        schon anonymisiert ist oder noch Bestellungen laufen.
    """
    if user.is_active or user.anonymized_at is not None or has_open_orders(db, user):
        return False
    _anonymize(db, user)
    return True


def anonymize_pending_accounts(db: Session) -> int:
    """Anonymisiert alle gelöschten Konten, deren Bestellungen inzwischen versendet sind.

    Läuft beim Start der App (app/main.py), damit kein Konto vergessen wird.

    Returns:
        Anzahl der Konten, die jetzt anonymisiert wurden.
    """
    waiting = db.scalars(select(User).where(User.is_active.is_(False), User.anonymized_at.is_(None))).all()
    return sum(anonymize_if_possible(db, user) for user in waiting)


def _anonymize(db: Session, user: User) -> None:
    """Entfernt alle persönlichen Daten eines gelöschten Kontos.

    Bleibt erhalten (gesetzliche Aufbewahrungspflicht für Bestell- und Rechnungsbelege):
        - die Bestellungen mit ihren Positionen, inkl. der darin kopierten Liefer- und
          Rechnungsadresse (orders.ship_* / bill_*),
        - Kundenbilder, die zu einer Bestellung gehören (für die Produktion bzw. als Beleg),
        - die Zeile in "users" selbst, damit die Bestellungen ihr Konto behalten
          (Mitarbeiter sehen "Konto gelöscht").

    Wird entfernt bzw. überschrieben:
        - Name, Anrede, E-Mail (Platzhalter, damit die Adresse für eine neue Registrierung frei wird),
          Passwort-Hash (danach passt kein Passwort mehr), offene E-Mail-Änderung,
        - gespeicherte Adressen, Bestätigungscodes, Sitzungen,
        - Profilbild (Datei und Pfad), Warenkorb und Kundenbilder ohne Bestellung (Dateien und Zeilen).
    """
    # Kundenbilder: nur die behalten, die in einer Bestellung stecken
    ordered_image_ids = set(
        db.scalars(select(OrderItem.customer_image_id).where(OrderItem.customer_image_id.is_not(None)))
    )
    db.execute(delete(CartItem).where(CartItem.user_id == user.id))
    for image in db.scalars(select(CustomerImage).where(CustomerImage.user_id == user.id)).all():
        if image.id not in ordered_image_ids:
            for path in (image.original_path, image.background_removed_path, image.processed_path):
                _delete_file(path)
            db.delete(image)

    db.execute(delete(Address).where(Address.user_id == user.id))
    db.execute(delete(VerificationCode).where(VerificationCode.user_id == user.id))
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))

    _delete_file(user.avatar_path)
    user.avatar_path = None
    user.email = f"geloescht-{user.id}@anonymisiert.invalid"  # ".invalid" ist eine Endung, die es nie geben wird
    user.first_name = None
    user.last_name = None
    user.salutation = None
    user.pending_email = None
    user.password_hash = "anonymisiert"  # kein gültiger Hash → verify_password ist immer False
    user.anonymized_at = datetime.now()
    db.commit()
