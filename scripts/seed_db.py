"""Legt die gemeinsamen Startdaten in der eigenen, lokalen laserflow.db an.

Die Datenbank selbst kommt nie ins Repo. Jeder im Team startet dieses Skript einmal
(und nach jedem Löschen von laserflow.db erneut) und hat danach dieselben Startdaten.

Aktuell: der erste Admin (US15). Ohne ihn könnte niemand die Mitarbeiter-Maske
benutzen, denn Mitarbeiter und Admins entstehen nur über diese Maske.

Starten (im Repo-Ordner, mit aktiver .venv):
    python -m scripts.seed_db

Das Skript fragt nach E-Mail, Vor- und Nachname und Passwort des Admins. Bei E-Mail und
Namen reicht Enter für den Standardwert. Das Passwort steht bewusst
nicht im Code, damit kein Passwort im Repo landet.

Mehrfach starten ist ungefährlich: Gibt es die E-Mail schon, wird nichts angelegt.
"""

from getpass import getpass

from app.accounts import employee_service
from app.accounts.service import AccountError, get_user_by_email
from app.database import SessionLocal, init_db

DEFAULT_ADMIN_EMAIL = "admin@laserflow.local"
DEFAULT_ADMIN_FIRST_NAME = "Admin"
DEFAULT_ADMIN_LAST_NAME = "LaserFlow"


def seed_first_admin(
    db,
    email: str,
    password: str,
    first_name: str = DEFAULT_ADMIN_FIRST_NAME,
    last_name: str = DEFAULT_ADMIN_LAST_NAME,
):
    """Legt den ersten Admin an, falls es die E-Mail noch nicht gibt.

    Args:
        db: Datenbank-Session.
        email: E-Mail des Admins.
        password: Passwort im Klartext (gespeichert wird nur der Hash).
        first_name, last_name: Name, wie er im Benutzermenü erscheint.

    Returns:
        der neue Admin oder None, wenn die E-Mail schon vergeben war.

    Raises:
        FieldValidationError: E-Mail, Passwort oder Name erfüllen die Regeln nicht.
    """
    if get_user_by_email(db, email) is not None:
        return None
    return employee_service.create_employee(db, email, password, first_name, last_name, "admin")


def main() -> None:
    """Fragt die Admin-Daten ab und legt den Admin an."""
    init_db()  # Tabellen anlegen, falls laserflow.db noch nicht existiert
    email = input(f"E-Mail des ersten Admins [{DEFAULT_ADMIN_EMAIL}]: ").strip() or DEFAULT_ADMIN_EMAIL
    first_name = input(f"Vorname [{DEFAULT_ADMIN_FIRST_NAME}]: ").strip() or DEFAULT_ADMIN_FIRST_NAME
    last_name = input(f"Nachname [{DEFAULT_ADMIN_LAST_NAME}]: ").strip() or DEFAULT_ADMIN_LAST_NAME
    password = getpass("Passwort (mind. 8 Zeichen, Buchstabe und Ziffer; wird nicht angezeigt): ")

    db = SessionLocal()
    try:
        admin = seed_first_admin(db, email, password, first_name, last_name)
    except AccountError as error:
        # detail ist ein Text oder eine Liste mit Meldung pro Feld
        messages = [item["msg"] for item in error.detail] if isinstance(error.detail, list) else [error.detail]
        print("Nicht angelegt: " + " ".join(messages))
        return
    finally:
        db.close()

    if admin is None:
        print(
            f"Es gibt schon ein Konto mit {email}. Nichts geändert. "
            "Den Namen kannst du als Admin auf mitarbeiter.html ändern (Stift)."
        )
    else:
        print(
            f"Admin {first_name} {last_name} ({email}) angelegt. "
            "Anmelden unter http://127.0.0.1:8000/anmelden.html"
        )


if __name__ == "__main__":
    main()
