"""Form der Daten für die Mitarbeiter-Endpunkte unter /api/admin/employees (US15).

FastAPI prüft damit nur, ob alle Felder da sind und den richtigen Typ haben (sonst 422).
Die inhaltlichen Regeln (E-Mail-Format, Passwortstärke, erlaubte Rollen) prüft
employee_service.py, damit die Meldungen auf Deutsch am richtigen Feld erscheinen.
"""

from pydantic import BaseModel, ConfigDict


class EmployeeCreateRequest(BaseModel):
    """Daten aus der Maske "Mitarbeiter anlegen" (frontend/mitarbeiter.html)."""

    email: str
    password: str
    first_name: str
    last_name: str
    role: str


class EmployeeUpdateRequest(BaseModel):
    """Daten aus der Maske im Bearbeiten-Modus.

    ``password`` ist optional: leer oder weggelassen = Passwort bleibt, wie es ist.
    """

    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    password: str | None = None


class EmployeeResponse(BaseModel):
    """Öffentliche Daten eines Mitarbeiters. Bewusst ohne Passwort-Hash."""

    # from_attributes: darf direkt aus einem User-Objekt der Datenbank gebaut werden
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str | None
    last_name: str | None
    role: str
    is_active: bool
