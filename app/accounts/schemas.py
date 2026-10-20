"""Form der Daten, die die Endpunkte unter /api/auth annehmen und zurückgeben.

FastAPI prüft damit automatisch, ob alle Felder da sind und den richtigen Typ haben
(sonst Antwort 422). Die inhaltlichen Regeln (Passwortstärke, PLZ ...) stehen in
validation.py, damit die Meldungen auf Deutsch und am richtigen Feld erscheinen.
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, computed_field


class RegisterRequest(BaseModel):
    """Daten aus dem Registrierungsformular (frontend/registrieren.html).

    Straße und Hausnummer kommen getrennt, damit jedes Feld seine eigene Prüfung
    und Fehlermeldung hat. Gespeichert werden sie zusammen (siehe service.register_user).
    """

    email: str
    password: str
    first_name: str
    last_name: str
    street: str
    house_number: str
    postal_code: str
    city: str


class RegisterResponse(BaseModel):
    """Antwort nach erfolgreicher Registrierung."""

    email: str
    message: str


class VerifyRequest(BaseModel):
    """Eingabe auf der Seite "E-Mail bestätigen" (frontend/bestaetigen.html)."""

    email: str
    code: str


class EmailRequest(BaseModel):
    """Nur eine E-Mail-Adresse, z. B. für "Code erneut senden"."""

    email: str


class LoginRequest(BaseModel):
    """Daten aus dem Anmeldeformular (frontend/anmelden.html)."""

    email: str
    password: str


def avatar_url_for(avatar_path: str | None) -> str | None:
    """Adresse, unter der der Browser das Profilbild lädt.

    Der Dateiname (ohne Endung) hängt als ?v=... dran. Er ändert sich mit jedem neuen Bild,
    deshalb lädt der Browser nach einem Wechsel das neue Bild statt das alte aus dem Cache.
    """
    if not avatar_path:
        return None
    return f"/api/account/avatar?v={Path(avatar_path).stem}"


class UserResponse(BaseModel):
    """Öffentliche Daten eines Kontos. Bewusst ohne Passwort-Hash."""

    # from_attributes: darf direkt aus einem User-Objekt der Datenbank gebaut werden
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str | None
    last_name: str | None
    role: str
    # Pfad im Dateisystem: nur intern, wird nicht mitgeschickt (exclude=True)
    avatar_path: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def avatar_url(self) -> str | None:
        """Adresse des Profilbilds für das Icon oben rechts (None = Standard-Symbol)."""
        return avatar_url_for(self.avatar_path)


# --------------------------------------------------------------------------- Mein Konto (US10)


class ProfileResponse(BaseModel):
    """Alle Daten für die Seite "Mein Konto"."""

    email: str
    pending_email: str | None
    first_name: str | None
    last_name: str | None
    street: str
    house_number: str
    postal_code: str
    city: str
    created_at: datetime
    avatar_path: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def avatar_url(self) -> str | None:
        """Adresse des Profilbilds (None = kein Bild)."""
        return avatar_url_for(self.avatar_path)


class ProfileUpdate(BaseModel):
    """Geänderte persönliche Daten (Name und Lieferadresse)."""

    first_name: str
    last_name: str
    street: str
    house_number: str
    postal_code: str
    city: str


class PasswordChange(BaseModel):
    """Passwort ändern: aktuelles Passwort zur Sicherheit, dazu das neue."""

    current_password: str
    new_password: str


class EmailChangeRequest(BaseModel):
    """Neue E-Mail-Adresse anfordern. Das Passwort bestätigt, dass wirklich der Kunde das will."""

    new_email: str
    password: str


class CodeRequest(BaseModel):
    """Nur ein Bestätigungscode."""

    code: str


class PasswordConfirm(BaseModel):
    """Nur das Passwort, z. B. zum Bestätigen von "Konto löschen"."""

    password: str


class PendingEmailResponse(BaseModel):
    """Antwort nach dem Anfordern einer neuen E-Mail-Adresse."""

    pending_email: str


class AvatarResponse(BaseModel):
    """Antwort nach dem Hochladen eines Profilbilds."""

    avatar_url: str | None
