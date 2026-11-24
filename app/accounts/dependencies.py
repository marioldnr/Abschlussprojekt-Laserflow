"""Login-Prüfung für Endpunkte (gemeinsamer Baustein, auch für andere Module).

Benutzung in einem Router:

    from app.accounts.dependencies import get_current_user

    @router.get("/etwas")
    def etwas(user: User = Depends(get_current_user)):
        ...

Rollenprüfung (Anmeldung plus erlaubte Rolle) über dieselben Bausteine:

    from app.accounts.dependencies import require_admin, require_employee

    @router.get("/mitarbeiter-bereich")
    def bereich(user: User = Depends(require_employee)):
        ...

    @router.get("/admin-bereich")
    def admin_bereich(user: User = Depends(require_admin)):
        ...

Ist niemand angemeldet, antwortet FastAPI automatisch mit 401 und der Endpunkt läuft gar nicht erst.
Ist jemand angemeldet, aber hat die falsche Rolle, antwortet der Server mit 403.
"""

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import config
from app.accounts import service
from app.accounts.models import User
from app.database import get_db


def get_session_token(
    session_token: str | None = Cookie(default=None, alias=config.SESSION_COOKIE_NAME),
) -> str | None:
    """Liest das Sitzungs-Token aus dem Cookie (None, wenn es keins gibt)."""
    return session_token


def get_current_user(
    db: Session = Depends(get_db),
    session_token: str | None = Depends(get_session_token),
) -> User:
    """Liefert das angemeldete Konto.

    Raises:
        HTTPException 401: niemand angemeldet, Sitzung abgelaufen oder Konto deaktiviert.
    """
    user = service.get_user_by_session(db, session_token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bitte melde dich an.")
    return user


MSG_EMPLOYEE_ONLY = "Diese Funktion ist nur für Mitarbeiter."
MSG_ADMIN_ONLY = "Diese Seite ist nur für Admins."


def require_roles(*roles: str, detail: str = MSG_EMPLOYEE_ONLY):
    """Baut eine Abhängigkeit, die nur angemeldete Konten mit einer der genannten Rollen durchlässt.

    Warum eine Fabrik an einer Stelle: Alle Rollenregeln laufen über diese Funktion, damit
    niemand eine Rollenprüfung von Hand nachbaut. Der Admin muss in ``roles`` ausdrücklich
    mit aufgezählt werden. Ein Admin hat sonst nicht automatisch die Rechte eines Mitarbeiters.

    Args:
        *roles: erlaubte Rollen, z. B. ``"employee"``, ``"admin"``. Mindestens eine.
        detail: Meldung, die bei 403 zurückkommt.

    Returns:
        die Abhängigkeit ``check``. Sie liefert das angemeldete Konto (``User``).

    Raises:
        ValueError: beim Aufbau, wenn keine Rolle angegeben wurde. Das ist ein Fehler im Code,
            kein Fehler des Nutzers, deshalb wird er sofort beim Start sichtbar.

    Bei der Benutzung (``check``):
        HTTPException 401: niemand angemeldet (kommt von get_current_user).
        HTTPException 403: angemeldet, aber die Rolle ist nicht erlaubt.
    """
    if not roles:
        raise ValueError("require_roles braucht mindestens eine Rolle.")

    def check(user: User = Depends(get_current_user)) -> User:
        """Lässt nur Konten mit erlaubter Rolle durch.

        Returns:
            das angemeldete Konto.

        Raises:
            HTTPException 403: Rolle nicht erlaubt.
        """
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
        return user

    return check


# Admin hat laut US15 alle Mitarbeiterrechte, deshalb steht "admin" hier mit drin.
require_employee = require_roles("employee", "admin")

require_admin = require_roles("admin", detail=MSG_ADMIN_ONLY)
