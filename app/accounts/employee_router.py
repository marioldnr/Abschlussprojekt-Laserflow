"""Endpunkte für US15: Mitarbeiteraccounts verwalten (/api/admin/employees).

Alle Endpunkte sind nur für angemeldete Admins. Die Abhängigkeit ``require_admin``
prüft die Rolle "admin"; die Anmeldung selbst prüft ``get_current_user`` aus
app/accounts/dependencies.py (gemeinsamer Baustein für alle Module).

    GET  /api/admin/employees        alle Mitarbeiter und Admins     200 / 401 / 403
    POST /api/admin/employees        Mitarbeiter anlegen             201 / 401 / 403 / 409 / 422
    GET  /api/admin/employees/{id}   einen Mitarbeiter holen         200 / 401 / 403 / 404
    PUT  /api/admin/employees/{id}   Mitarbeiter bearbeiten          200 / 400 / 401 / 403 / 404 / 409 / 422

Der Router macht nur HTTP: Daten annehmen, Service aufrufen, Antwort zurückgeben.
Die Logik steht in employee_service.py.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.accounts import employee_service, service
from app.accounts.dependencies import get_current_user
from app.accounts.employee_schemas import EmployeeCreateRequest, EmployeeResponse, EmployeeUpdateRequest
from app.accounts.models import User
from app.database import get_db

router = APIRouter(prefix="/api/admin/employees", tags=["Mitarbeiter verwalten (Admin)"])

MSG_ADMIN_ONLY = "Diese Seite ist nur für Admins."


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Lässt nur angemeldete Admins durch (Akzeptanzkriterium: Mitarbeiter haben keinen Zugriff).

    Wird per ``Depends(require_admin)`` an jeden Endpunkt gehängt.

    Warum ``get_current_user`` und keine eigene Cookie-Prüfung: Die Anmeldung wird an einer
    Stelle geprüft, und zwar für alle Module gleich. Ändert sich etwas an der Sitzung
    (Ablauf, deaktiviertes Konto), wirkt das überall. Hier wird nur noch die Rolle geprüft.

    Returns:
        der angemeldete Admin.

    Raises:
        HTTPException 401: niemand angemeldet (kommt von get_current_user).
        HTTPException 403: angemeldet, aber nicht Admin (Kunde oder Mitarbeiter).
    """
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MSG_ADMIN_ONLY)
    return user


def _http_error(error: service.AccountError) -> HTTPException:
    """Wandelt einen Fehler aus dem Service in eine HTTP-Antwort {"detail": ...} um."""
    return HTTPException(status_code=error.status_code, detail=error.detail)


@router.get("", response_model=list[EmployeeResponse])
def list_employees(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Liefert alle Mitarbeiter und Admins für die Übersicht (Rollen einsehen)."""
    return employee_service.list_employees(db)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=EmployeeResponse)
def create_employee(
    data: EmployeeCreateRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    """Legt einen Mitarbeiter oder Admin an.

    Antworten: 201 angelegt · 409 E-Mail schon vergeben · 422 ungültige Eingaben
    (detail = Liste mit Meldung pro Feld, wie bei der Registrierung).
    """
    try:
        return employee_service.create_employee(
            db, data.email, data.password, data.first_name, data.last_name, data.role
        )
    except service.AccountError as error:
        raise _http_error(error) from error


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(employee_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Liefert einen Mitarbeiter. 404, wenn es ihn nicht gibt oder es ein Kunde ist."""
    try:
        return employee_service.get_employee(db, employee_id)
    except service.AccountError as error:
        raise _http_error(error) from error


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    data: EmployeeUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Ändert Daten, Rolle und Status eines Mitarbeiters (Passwort nur, wenn angegeben).

    Antworten: 200 geändert · 400 letzter aktiver Admin oder Konto schon deaktiviert ·
    404 nicht gefunden · 409 E-Mail vergeben · 422 ungültige Eingaben.
    """
    try:
        return employee_service.update_employee(
            db,
            employee_id,
            data.email,
            data.first_name,
            data.last_name,
            data.role,
            data.is_active,
            data.password,
        )
    except service.AccountError as error:
        raise _http_error(error) from error
