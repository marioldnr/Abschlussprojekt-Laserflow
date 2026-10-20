"""Logik für Registrieren, E-Mail bestätigen, Anmelden und Abmelden.

Ablauf:
    1. register_user():     Konto + Adresse anlegen (noch nicht bestätigt),
                            4-stelligen Code erzeugen und per E-Mail schicken.
    2. verify_code():       Code prüfen. Richtig → Konto ist bestätigt.
       resend_code():       neuen Code schicken (der alte gilt dann nicht mehr).
    3. authenticate():      E-Mail und Passwort prüfen (nur bestätigte Konten).
    4. create_session():    nach Bestätigung oder Anmeldung eine Sitzung anlegen,
       get_user_by_session(), delete_session(): Sitzung lesen bzw. beenden (Abmelden).

Die Funktionen kennen kein HTTP. Geht etwas schief, werfen sie einen AccountError
mit Status-Code und Meldung; der Router macht daraus die HTTP-Antwort.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config
from app.accounts.models import Address, User, UserSession, VerificationCode
from app.accounts.schemas import RegisterRequest
from app.accounts.validation import validate_registration
from app.mail import send_mail

# --------------------------------------------------------------------------- Fehler


class AccountError(Exception):
    """Basis für alle erwarteten Fehler in diesem Modul.

    Attributes:
        status_code: passender HTTP-Status (der Router gibt ihn weiter).
        detail: Meldung für die Anzeige im Frontend (Text oder Liste von Feldfehlern).
    """

    status_code = 400

    def __init__(self, detail):
        super().__init__(detail)
        self.detail = detail


class FieldValidationError(AccountError):
    """Eingaben in einem Formular sind ungültig (422).

    ``detail`` hat dasselbe Format wie die Fehler, die FastAPI selbst erzeugt:
    [{"loc": ["body", "<feld>"], "msg": "<meldung>"}, ...]. So kann das Frontend
    jede Meldung unter dem passenden Feld anzeigen.
    """

    status_code = 422

    def __init__(self, errors: dict[str, str]):
        super().__init__([{"loc": ["body", field], "msg": message} for field, message in errors.items()])
        self.errors = errors


class RegistrationInvalidError(FieldValidationError):
    """Eingaben bei der Registrierung sind ungültig (422)."""


class EmailAlreadyRegisteredError(AccountError):
    """Die E-Mail-Adresse gehört schon zu einem Konto (409)."""

    status_code = 409


class AlreadyVerifiedError(AccountError):
    """Das Konto ist schon bestätigt, ein Code wird nicht mehr gebraucht (409)."""

    status_code = 409


class CodeInvalidError(AccountError):
    """Der eingegebene Code ist falsch (400)."""

    status_code = 400


class CodeExpiredError(AccountError):
    """Der Code ist abgelaufen oder schon benutzt (410 = "nicht mehr da")."""

    status_code = 410


class TooManyAttemptsError(AccountError):
    """Zu viele falsche Codes hintereinander (429 = "zu viele Anfragen")."""

    status_code = 429


class InvalidCredentialsError(AccountError):
    """E-Mail oder Passwort falsch (401)."""

    status_code = 401


class AccountNotVerifiedError(AccountError):
    """Passwort stimmt, aber das Konto ist noch nicht bestätigt (403)."""

    status_code = 403


# Meldungen an einer Stelle, damit Tests und Frontend dieselben Texte sehen.
MSG_EMAIL_TAKEN = "Diese E-Mail-Adresse ist bereits registriert."
MSG_ALREADY_VERIFIED = "Dein Konto ist bereits bestätigt. Du kannst dich anmelden."
MSG_CODE_WRONG = "Der Code ist falsch."
MSG_CODE_EXPIRED = "Der Code ist abgelaufen. Bitte fordere einen neuen Code an."
MSG_TOO_MANY = "Zu viele falsche Versuche. Bitte fordere einen neuen Code an."
MSG_INVALID_CREDENTIALS = "E-Mail-Adresse oder Passwort ist falsch."
MSG_NOT_VERIFIED = "Dein Konto ist noch nicht bestätigt."

# --------------------------------------------------------------------------- Passwort

# Einstellungen für scrypt (in Python eingebaut, kein Zusatzpaket nötig).
# scrypt ist absichtlich langsam und braucht viel Speicher. Das bremst Angreifer, die
# gestohlene Hashes mit Millionen Passwörtern durchprobieren wollen.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def hash_password(password: str) -> str:
    """Erzeugt einen Hash zum Speichern in users.password_hash.

    Jedes Passwort bekommt ein eigenes zufälliges "Salz". Dadurch haben zwei Kunden mit
    demselben Passwort trotzdem verschiedene Hashes.

    Returns:
        Text der Form "scrypt$n$r$p$<salz hex>$<hash hex>". Alles, was man zum späteren
        Prüfen braucht, steht darin.
    """
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Prüft, ob ein eingegebenes Passwort zum gespeicherten Hash passt.

    Rechnet mit demselben Salz neu und vergleicht. ``hmac.compare_digest`` vergleicht
    in immer gleicher Zeit, damit man an der Antwortzeit nichts ablesen kann.

    Returns:
        True, wenn das Passwort stimmt. False auch bei einem kaputten Hash.
    """
    try:
        algorithm, n, r, p, salt_hex, digest_hex = stored_hash.split("$")
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p), dklen=32
        )
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


# --------------------------------------------------------------------------- Hilfen


def normalize_email(email: str) -> str:
    """Entfernt Leerzeichen und schreibt klein, damit Max@Web.de und max@web.de ein Konto sind."""
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Sucht ein Konto über die E-Mail-Adresse (Groß-/Kleinschreibung egal)."""
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def _generate_code() -> str:
    """Zufälliger 4-stelliger Code, auch mit führenden Nullen (z. B. "0427").

    ``secrets`` statt ``random``: secrets ist für Sicherheitszwecke gedacht und
    nicht vorhersagbar.
    """
    return f"{secrets.randbelow(10_000):04d}"


def _verification_mail_text(first_name: str | None, code: str) -> str:
    """Standardtext der Bestätigungs-E-Mail."""
    greeting = f"Hallo {first_name}," if first_name else "Hallo,"
    return (
        f"{greeting}\n\n"
        + "danke für deine Registrierung bei LaserFlow.\n\n"
        + f"Dein Bestätigungscode lautet: {code}\n\n"
        + f"Der Code ist {config.VERIFICATION_CODE_VALID_MINUTES} Minuten gültig. "
        + "Falls du dich nicht registriert hast, kannst du diese E-Mail ignorieren.\n\n"
        + "Dein LaserFlow-Team"
    )


def create_and_send_code(db: Session, user: User, to: str | None = None, mail_text=None) -> str:
    """Speichert einen neuen Code für das Konto und schickt ihn per E-Mail.

    Args:
        db: Datenbank-Session.
        user: das Konto, zu dem der Code gehört.
        to: Empfänger. Standard: die E-Mail des Kontos. Beim Ändern der E-Mail (US10)
            geht der Code an die neue Adresse.
        mail_text: Funktion (Vorname, Code) → Text. Standard: Text für die Registrierung.

    Returns:
        der erzeugte Code (wird z. B. in Tests gebraucht).
    """
    code = _generate_code()
    db.add(VerificationCode(user=user, code=code))
    db.commit()
    text = (mail_text or _verification_mail_text)(user.first_name, code)
    send_mail(to or user.email, "Dein LaserFlow-Bestätigungscode", text)
    return code

def _latest_code(db: Session, user: User) -> VerificationCode | None:
    """Der neueste Code eines Kontos. Nur dieser gilt."""
    return db.scalar(
        select(VerificationCode)
        .where(VerificationCode.user_id == user.id)
        .order_by(VerificationCode.created_at.desc(), VerificationCode.id.desc())
    )


# --------------------------------------------------------------------------- 1. Registrieren


def register_user(db: Session, data: RegisterRequest) -> User:
    """Legt ein neues, noch nicht bestätigtes Kundenkonto an und verschickt den Code.

    Args:
        db: Datenbank-Session.
        data: Eingaben aus dem Registrierungsformular.

    Returns:
        das neue Konto.

    Raises:
        RegistrationInvalidError: mindestens ein Feld ist ungültig (mit Meldung pro Feld).
        EmailAlreadyRegisteredError: die E-Mail-Adresse ist schon vergeben.
    """
    errors = validate_registration(data.model_dump())
    if errors:
        raise RegistrationInvalidError(errors)

    if get_user_by_email(db, data.email) is not None:
        raise EmailAlreadyRegisteredError(MSG_EMAIL_TAKEN)

    user = User(
        email=normalize_email(data.email),
        password_hash=hash_password(data.password),
        role="customer",
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
    )
    # Die Adresse aus dem Formular wird als Lieferadresse gespeichert.
    # Straße und Hausnummer kommen getrennt, stehen aber in EINER Spalte ("Musterstraße 12"):
    # So ist es im Datenmodell festgelegt (CLAUDE.md, Abschnitt Datenbank), und Bestellungen
    # kopieren die Adresse genau in dieser Form.
    street_with_number = f"{data.street.strip()} {data.house_number.strip()}"
    user.addresses.append(
        Address(type="shipping", street=street_with_number, postal_code=data.postal_code.strip(), city=data.city.strip())
    )
    db.add(user)
    try:
        db.flush()  # schreibt den User schon, damit die Datenbank doppelte E-Mails ablehnen kann
    except IntegrityError:
        # Sehr selten: zwei Anfragen mit derselben E-Mail gleichzeitig. Die Datenbank
        # (unique=True) verhindert das zweite Konto, wir melden es wie oben.
        db.rollback()
        raise EmailAlreadyRegisteredError(MSG_EMAIL_TAKEN) from None

    create_and_send_code(db, user)  # speichert (commit) und verschickt die E-Mail
    return user


# --------------------------------------------------------------------------- 2. Bestätigen


def verify_code(db: Session, email: str, code: str) -> User:
    """Prüft den Bestätigungscode und bestätigt bei Erfolg das Konto.

    Args:
        db: Datenbank-Session.
        email: E-Mail-Adresse des Kontos.
        code: eingegebener Code.

    Returns:
        das jetzt bestätigte Konto.

    Raises:
        AlreadyVerifiedError: Konto ist schon bestätigt.
        CodeExpiredError: kein gültiger Code mehr (abgelaufen oder schon benutzt).
        TooManyAttemptsError: zu viele Fehlversuche mit diesem Code.
        CodeInvalidError: Code falsch (oder unbekannte E-Mail, damit man nicht
            herausfinden kann, welche Adressen registriert sind).
    """
    user = get_user_by_email(db, email)
    if user is None:
        raise CodeInvalidError(MSG_CODE_WRONG)
    if user.is_verified:
        raise AlreadyVerifiedError(MSG_ALREADY_VERIFIED)

    check_and_use_code(db, user, code)
    user.is_verified = True
    db.commit()
    return user


def check_and_use_code(db: Session, user: User, code: str) -> None:
    """Prüft einen Bestätigungscode und markiert ihn bei Erfolg als benutzt.

    Gemeinsame Prüfung für die Registrierung (US02) und das Ändern der E-Mail (US10).
    Speichert (commit) nur die Fehlversuche; was nach einem richtigen Code passiert,
    entscheidet die aufrufende Funktion und speichert es selbst.

    Raises:
        CodeExpiredError: kein gültiger Code (abgelaufen, schon benutzt oder nie angefordert).
        TooManyAttemptsError: zu viele Fehlversuche mit diesem Code.
        CodeInvalidError: Code falsch, mit Anzahl der restlichen Versuche.
    """
    latest = _latest_code(db, user)
    if latest is None or latest.used_at is not None:
        raise CodeExpiredError(MSG_CODE_EXPIRED)
    if latest.failed_attempts >= config.VERIFICATION_CODE_MAX_ATTEMPTS:
        raise TooManyAttemptsError(MSG_TOO_MANY)
    if datetime.now() > latest.created_at + timedelta(minutes=config.VERIFICATION_CODE_VALID_MINUTES):
        raise CodeExpiredError(MSG_CODE_EXPIRED)

    # encode(): compare_digest mag nur Bytes oder reine ASCII-Texte, Eingaben wie "é" wären sonst ein Absturz
    if not hmac.compare_digest(latest.code.encode(), code.strip().encode()):
        latest.failed_attempts += 1
        db.commit()
        remaining = config.VERIFICATION_CODE_MAX_ATTEMPTS - latest.failed_attempts
        if remaining <= 0:
            raise TooManyAttemptsError(MSG_TOO_MANY)
        word = "Versuch" if remaining == 1 else "Versuche"
        raise CodeInvalidError(f"{MSG_CODE_WRONG} Du hast noch {remaining} {word}.")

    latest.used_at = datetime.now()

def resend_code(db: Session, email: str) -> None:
    """Schickt einen neuen Code. Danach gilt nur noch der neue.

    Gibt bewusst nie einen Fehler zurück, auch nicht bei unbekannter E-Mail. Sonst
    könnte man über diese Funktion testen, welche Adressen registriert sind.
    """
    user = get_user_by_email(db, email)
    if user is not None and not user.is_verified and user.is_active:
        create_and_send_code(db, user)


# --------------------------------------------------------------------------- 3. Anmelden


def authenticate(db: Session, email: str, password: str) -> User:
    """Prüft E-Mail und Passwort.

    Returns:
        das Konto, wenn die Daten stimmen und es bestätigt ist.

    Raises:
        InvalidCredentialsError: E-Mail unbekannt, Passwort falsch oder Konto
            deaktiviert/anonymisiert. Immer dieselbe Meldung, damit niemand
            herausfinden kann, ob eine E-Mail registriert ist.
        AccountNotVerifiedError: Daten stimmen, Konto aber noch nicht bestätigt.
            (Wird erst nach dem richtigen Passwort gemeldet, aus demselben Grund.)
    """
    user = get_user_by_email(db, email)
    if (
        user is None
        or not user.is_active
        or user.anonymized_at is not None
        or not verify_password(password, user.password_hash)
    ):
        raise InvalidCredentialsError(MSG_INVALID_CREDENTIALS)
    if not user.is_verified:
        raise AccountNotVerifiedError(MSG_NOT_VERIFIED)
    return user


# --------------------------------------------------------------------------- 4. Sitzung


def create_session(db: Session, user: User) -> str:
    """Legt eine neue Sitzung an (= der Kunde ist angemeldet).

    Returns:
        das Token, das als Cookie an den Browser geht.
    """
    token = secrets.token_urlsafe(32)  # 43 Zeichen, praktisch nicht zu erraten
    expires_at = datetime.now() + timedelta(days=config.SESSION_VALID_DAYS)
    db.add(UserSession(user_id=user.id, token=token, expires_at=expires_at))
    db.commit()
    return token


def get_user_by_session(db: Session, token: str | None) -> User | None:
    """Findet das angemeldete Konto zu einem Sitzungs-Token.

    Returns:
        das Konto oder None (kein Token, unbekannt, abgelaufen oder Konto deaktiviert).
    """
    if not token:
        return None
    session = db.scalar(select(UserSession).where(UserSession.token == token))
    if session is None:
        return None
    if session.expires_at < datetime.now():
        db.delete(session)  # abgelaufene Sitzung gleich aufräumen
        db.commit()
        return None
    user = session.user
    if not user.is_active or user.anonymized_at is not None:
        return None
    return user


def delete_session(db: Session, token: str | None) -> None:
    """Beendet eine Sitzung (Abmelden). Unbekannte Tokens werden still ignoriert."""
    if not token:
        return
    session = db.scalar(select(UserSession).where(UserSession.token == token))
    if session is not None:
        db.delete(session)
        db.commit()
