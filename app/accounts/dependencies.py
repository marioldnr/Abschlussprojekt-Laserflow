"""Login-Prüfung für Endpunkte (gemeinsamer Baustein, auch für andere Module).

Benutzung in einem Router:

    from app.accounts.dependencies import get_current_user

    @router.get("/etwas")
    def etwas(user: User = Depends(get_current_user)):
        ...

Ist niemand angemeldet, antwortet FastAPI automatisch mit 401 und der Endpunkt läuft gar nicht erst.
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
