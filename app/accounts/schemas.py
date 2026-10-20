"""Form der Daten, die die Endpunkte unter /api/auth annehmen und zurückgeben.

FastAPI prüft damit automatisch, ob alle Felder da sind und den richtigen Typ haben
(sonst Antwort 422). Die inhaltlichen Regeln (Passwortstärke, PLZ ...) stehen in
validation.py, damit die Meldungen auf Deutsch und am richtigen Feld erscheinen.
"""

from pydantic import BaseModel, ConfigDict


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


class UserResponse(BaseModel):
    """Öffentliche Daten eines Kontos. Bewusst ohne Passwort-Hash."""

    # from_attributes: darf direkt aus einem User-Objekt der Datenbank gebaut werden
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str | None
    last_name: str | None
    role: str
