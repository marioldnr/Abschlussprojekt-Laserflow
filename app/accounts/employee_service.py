"""Logik für US15: Mitarbeiteraccounts verwalten (nur für Admins).

Ablauf:
    create_employee():  Admin legt einen Mitarbeiter- oder Admin-Account an.
    list_employees():   alle Mitarbeiter und Admins für die Übersicht.
    get_employee():     einen Mitarbeiter über seine ID holen.
    update_employee():  Daten und Rolle eines Mitarbeiters nachträglich ändern.

Baut auf dem Modul accounts auf: Passwort-Hash, E-Mail-Normalisierung und Fehlerklassen
kommen aus service.py, die Prüfregeln aus validation.py. So gelten für Mitarbeiter
dieselben Regeln wie bei der Registrierung.

Bewusste Entscheidungen:
    - Eigene Datei statt service.py, damit sich US15 und die Registrierung (US02/US03)
      nicht in die Quere kommen.
    - Mitarbeiter liegen in der Tabelle users, Unterschied nur über die Spalte role.
    - Über diese Funktionen kann nie ein Kunde (role "customer") entstehen oder bearbeitet
      werden. Mitarbeiter entstehen nur hier, nicht über die öffentliche Registrierung.
    - "Account löschen" heißt deaktivieren (``is_active`` = False, Entscheidung des PO am
      20.10.2026): Der Account bleibt mit allen Daten erhalten, kann sich nicht mehr anmelden
      und ist endgültig. Ein deaktiviertes Konto wird nicht reaktiviert und nicht mehr
      bearbeitet (EmployeeInactiveError). Dafür reicht update_employee().
    - Es bleibt immer mindestens ein aktiver Admin (sonst könnte niemand mehr
      Mitarbeiter verwalten).
    - Wer Admin ist, prüft der Router (die Funktionen kennen kein HTTP und keine Sitzung).
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.accounts.service import (
    MSG_EMAIL_TAKEN,
    AccountError,
    EmailAlreadyRegisteredError,
    FieldValidationError,
    get_user_by_email,
    hash_password,
    normalize_email,
)
from app.accounts.validation import check_email, check_name, check_password

# Rollen, die über die Mitarbeiter-Maske vergeben werden dürfen ("customer" bewusst nicht).
EMPLOYEE_ROLES = ("employee", "admin")

MSG_ROLE_INVALID = "Bitte wähle eine gültige Rolle (Mitarbeiter oder Admin)."
MSG_EMPLOYEE_NOT_FOUND = "Mitarbeiter nicht gefunden."
MSG_LAST_ADMIN = "Es muss mindestens ein aktiver Admin bleiben."
MSG_EMPLOYEE_INACTIVE = "Dieses Konto ist deaktiviert und kann nicht mehr geändert werden."


class EmployeeNotFoundError(AccountError):
    """Es gibt keinen Mitarbeiter oder Admin mit dieser ID (404)."""

    status_code = 404


class LastAdminError(AccountError):
    """Die Änderung würde den letzten aktiven Admin entfernen (400).

    Ohne aktiven Admin könnte niemand mehr Mitarbeiter verwalten.
    Bewusst 400 und nicht 409: 409 bedeutet bei uns "E-Mail schon vergeben", so kann
    die Maske beide Fälle am Status-Code unterscheiden.
    """

    status_code = 400


class EmployeeInactiveError(AccountError):
    """Der Account ist deaktiviert und darf nicht mehr geändert werden (400).

    Deaktivieren ist endgültig (PO-Entscheidung 20.10.2026): Ein deaktivierter Account
    wird weder reaktiviert noch anders bearbeitet. Bewusst 400, wie LastAdminError,
    damit die Maske den Fehler als allgemeine Meldung anzeigt.
    """

    status_code = 400


def _check_role(role: str) -> str | None:
    """Prüft, ob die Rolle über die Mitarbeiter-Maske vergeben werden darf."""
    if role not in EMPLOYEE_ROLES:
        return MSG_ROLE_INVALID
    return None


def _collect_errors(checks: dict[str, str | None]) -> dict[str, str]:
    """Behält nur die Felder, bei denen eine Prüfung einen Fehlertext geliefert hat.

    Warum sammeln statt beim ersten Fehler abbrechen: Die Maske soll alle falschen
    Felder auf einmal anzeigen, sonst muss der Admin mehrmals absenden.
    """
    return {field: message for field, message in checks.items() if message}


def create_employee(
    db: Session, email: str, password: str, first_name: str, last_name: str, role: str
) -> User:
    """Legt einen Mitarbeiter- oder Admin-Account an (US15).

    Mitarbeiter werden vom Admin angelegt und brauchen keinen Bestätigungscode,
    deshalb ist ``is_verified`` sofort True (sonst lässt authenticate() sie nicht rein).

    Args:
        db: Datenbank-Session.
        email: E-Mail-Adresse (wird normalisiert gespeichert).
        password: Startpasswort im Klartext, gespeichert wird nur der Hash.
        first_name: Vorname.
        last_name: Nachname.
        role: "employee" oder "admin".

    Returns:
        der neue Account.

    Raises:
        FieldValidationError: ein Feld oder die Rolle ist ungültig (422, Meldung pro Feld).
        EmailAlreadyRegisteredError: die E-Mail-Adresse ist schon vergeben (409).
    """
    # 1. Prüfen: alle Fehler sammeln, erst dann abbrechen
    errors = _collect_errors(
        {
            "email": check_email(email),
            "password": check_password(password),
            "first_name": check_name(first_name),
            "last_name": check_name(last_name),
            "role": _check_role(role),
        }
    )
    if errors:
        raise FieldValidationError(errors)

    # 2. Mit der Datenbank vergleichen: E-Mail schon vergeben?
    if get_user_by_email(db, email) is not None:
        raise EmailAlreadyRegisteredError(MSG_EMAIL_TAKEN)

    # 3. Speichern
    user = User(
        email=normalize_email(email),
        password_hash=hash_password(password),
        role=role,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        is_verified=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Sehr selten: dieselbe E-Mail kommt gleichzeitig ein zweites Mal an.
        # unique=True in der Tabelle verhindert das zweite Konto.
        db.rollback()
        raise EmailAlreadyRegisteredError(MSG_EMAIL_TAKEN) from None
    db.refresh(user)
    return user


def list_employees(db: Session) -> list[User]:
    """Liefert alle Mitarbeiter und Admins, sortiert nach Nachname und Vorname.

    Kunden sind nicht dabei. Deaktivierte Accounts sind dabei, damit die Übersicht
    alle Mitarbeiter zeigt (sie sind nur nicht mehr bearbeitbar).
    """
    return list(
        db.scalars(
            select(User)
            .where(User.role.in_(EMPLOYEE_ROLES))
            .order_by(User.last_name, User.first_name, User.id)
        )
    )


def _count_active_admins(db: Session) -> int:
    """Zählt die aktiven Admins."""
    return len(list(db.scalars(select(User.id).where(User.role == "admin", User.is_active.is_(True)))))


def get_employee(db: Session, employee_id: int) -> User:
    """Holt einen Mitarbeiter oder Admin über seine ID.

    Raises:
        EmployeeNotFoundError: keine ID gefunden oder der Account ist ein Kunde (404).
            Kunden gelten hier als "nicht gefunden", damit die Maske sie nie ändern kann.
    """
    user = db.get(User, employee_id)
    if user is None or user.role not in EMPLOYEE_ROLES:
        raise EmployeeNotFoundError(MSG_EMPLOYEE_NOT_FOUND)
    return user


def update_employee(
    db: Session,
    employee_id: int,
    email: str,
    first_name: str,
    last_name: str,
    role: str,
    is_active: bool,
    password: str | None = None,
) -> User:
    """Ändert die Daten eines bestehenden Mitarbeiters (US15: "nachträglich bearbeiten").

    Args:
        db: Datenbank-Session.
        employee_id: ID des Accounts.
        email, first_name, last_name, role: neue Werte (Prüfung wie beim Anlegen).
        is_active: False deaktiviert den Account endgültig (Löschen nur per Flag).
        password: neues Passwort. None oder leer = Passwort bleibt unverändert.

    Returns:
        der geänderte Account.

    Raises:
        EmployeeNotFoundError: keinen Mitarbeiter mit dieser ID gefunden (404).
        EmployeeInactiveError: der Account ist schon deaktiviert, also nicht mehr änderbar (400).
            Die Prüfung kommt vor allen anderen, auch vor den Feldprüfungen.
        FieldValidationError: ein Feld oder die Rolle ist ungültig (422).
        EmailAlreadyRegisteredError: die neue E-Mail gehört schon einem anderen Konto (409).
        LastAdminError: der letzte aktive Admin würde herabgestuft oder deaktiviert (400).
    """
    user = get_employee(db, employee_id)
    # Deaktivieren ist endgültig: Ein deaktiviertes Konto bleibt unverändert, auch
    # is_active=True wird nicht angenommen (keine Reaktivierung).
    if not user.is_active:
        raise EmployeeInactiveError(MSG_EMPLOYEE_INACTIVE)

    checks = {
        "email": check_email(email),
        "first_name": check_name(first_name),
        "last_name": check_name(last_name),
        "role": _check_role(role),
    }
    if password:
        checks["password"] = check_password(password)
    errors = _collect_errors(checks)
    if errors:
        raise FieldValidationError(errors)

    # Der letzte aktive Admin darf weder herabgestuft noch deaktiviert werden.
    loses_admin = user.role == "admin" and user.is_active and (role != "admin" or not is_active)
    if loses_admin and _count_active_admins(db) <= 1:
        raise LastAdminError(MSG_LAST_ADMIN)

    # Die eigene E-Mail darf bleiben, nur eine fremde ist "vergeben".
    owner = get_user_by_email(db, email)
    if owner is not None and owner.id != user.id:
        raise EmailAlreadyRegisteredError(MSG_EMAIL_TAKEN)

    user.email = normalize_email(email)
    user.first_name = first_name.strip()
    user.last_name = last_name.strip()
    user.role = role
    user.is_active = is_active
    if password:
        user.password_hash = hash_password(password)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise EmailAlreadyRegisteredError(MSG_EMAIL_TAKEN) from None
    db.refresh(user)
    return user
