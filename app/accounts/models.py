"""Datenbank-Tabellen des Moduls accounts.

Tabellen:
    users              Kunden, Mitarbeiter und Admins (Unterschied über die Spalte role)
    verification_codes Bestätigungen der Registrierung (US02)
    addresses          Adressen eines Kunden (Liefer- und Rechnungsadresse)
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Ein Benutzerkonto.

    Bewusste Entscheidungen:
        - Nur eine Tabelle für alle Rollen, die Rolle steht in ``role``
          ("customer", "employee", "admin").
        - Konten werden nicht gelöscht, sondern deaktiviert (``is_active``) bzw.
          anonymisiert (``anonymized_at``, US10), damit alte Bestellungen erhalten bleiben.
        - Das Passwort wird nie im Klartext gespeichert, nur als Hash.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="customer")
    salutation: Mapped[str | None] = mapped_column(String(20))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    is_verified: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    anonymized_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    # Verbindungen zu anderen Tabellen (keine eigenen Spalten, nur Python-Komfort)
    verification_codes: Mapped[list["VerificationCode"]] = relationship(back_populates="user")
    addresses: Mapped[list["Address"]] = relationship(back_populates="user")


class VerificationCode(Base):
    """Bestätigung einer Registrierung (US02).

    Hinweis: Ob per 4-stelligem Code oder per Link bestätigt wird, ist in Story 2 noch
    offen. Die Spalte ``code`` ist deshalb lang genug für beides (Code oder Link-Token).
    ``used_at`` ist leer, solange die Bestätigung noch nicht benutzt wurde.
    """

    __tablename__ = "verification_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    code: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    used_at: Mapped[datetime | None]

    user: Mapped["User"] = relationship(back_populates="verification_codes")


class Address(Base):
    """Adresse eines Kunden.

    Bewusste Entscheidungen:
        - ``type`` unterscheidet "shipping" (Lieferadresse) und "billing" (Rechnungsadresse).
        - ``street`` enthält Straße und Hausnummer zusammen, so wie das
          Registrierungsformular sie schickt (docs/module/anmeldung.md).
        - Beim Bestellen wird die Adresse in die Bestellung kopiert, damit spätere
          Änderungen alte Bestellungen nicht verändern.
    """

    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(20), default="shipping")
    street: Mapped[str] = mapped_column(String(200))
    postal_code: Mapped[str] = mapped_column(String(5))
    city: Mapped[str] = mapped_column(String(100))

    user: Mapped["User"] = relationship(back_populates="addresses")
