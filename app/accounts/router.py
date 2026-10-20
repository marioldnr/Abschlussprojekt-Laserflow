"""Endpunkte für Registrieren, E-Mail bestätigen, Anmelden und Abmelden (/api/auth/...).

Der Router macht nur HTTP: Daten annehmen, Service aufrufen, Antwort und Cookie setzen.
Die eigentliche Logik steht in service.py.

    POST /api/auth/register     Konto anlegen, Code per E-Mail          201 / 409 / 422
    POST /api/auth/verify       Code prüfen, danach angemeldet          200 / 400 / 409 / 410 / 429
    POST /api/auth/resend-code  neuen Code schicken                     204
    POST /api/auth/login        anmelden                                200 / 401 / 403
    GET  /api/auth/me           wer ist angemeldet?                     200 / 401
    POST /api/auth/logout       abmelden                                204
"""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import config
from app.accounts import service
from app.accounts.schemas import (
    EmailRequest,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
    VerifyRequest,
)
from app.database import get_db

router = APIRouter(prefix="/api/auth", tags=["Anmeldung und Registrierung"])


def _http_error(error: service.AccountError) -> HTTPException:
    """Wandelt einen Fehler aus dem Service in eine HTTP-Antwort {"detail": ...} um."""
    return HTTPException(status_code=error.status_code, detail=error.detail)


def _start_session(db: Session, user, response: Response) -> None:
    """Meldet den Kunden an: Sitzung anlegen und als Cookie an den Browser schicken.

    httponly: JavaScript kann das Cookie nicht lesen (Schutz, falls fremdes Skript auf die Seite kommt).
    samesite="lax": fremde Seiten können das Cookie nicht für versteckte Anfragen benutzen.
    Kein secure=True, weil LaserFlow lokal über http läuft (bei https einschalten).
    """
    token = service.create_session(db, user)
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=token,
        max_age=config.SESSION_VALID_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Legt ein Konto an und schickt den Bestätigungscode an die E-Mail-Adresse.

    Antworten: 201 angelegt · 409 E-Mail schon registriert · 422 ungültige Eingaben
    (detail = Liste mit Meldung pro Feld).
    """
    try:
        user = service.register_user(db, data)
    except service.AccountError as error:
        raise _http_error(error) from error
    return RegisterResponse(email=user.email, message="Wir haben dir einen Bestätigungscode geschickt.")


@router.post("/verify", response_model=UserResponse)
def verify(data: VerifyRequest, response: Response, db: Session = Depends(get_db)):
    """Prüft den Bestätigungscode. Bei Erfolg ist das Konto bestätigt und der Kunde angemeldet.

    Antworten: 200 Kundendaten + Sitzungs-Cookie · 400 Code falsch · 409 schon bestätigt ·
    410 Code abgelaufen · 429 zu viele Fehlversuche.
    """
    try:
        user = service.verify_code(db, data.email, data.code)
    except service.AccountError as error:
        raise _http_error(error) from error
    _start_session(db, user, response)
    return user


@router.post("/resend-code", status_code=status.HTTP_204_NO_CONTENT)
def resend_code(data: EmailRequest, db: Session = Depends(get_db)):
    """Schickt einen neuen Code. Antwortet immer mit 204, auch bei unbekannter E-Mail."""
    service.resend_code(db, data.email)


@router.post("/login", response_model=UserResponse)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Meldet einen Kunden an.

    Antworten: 200 Kundendaten + Sitzungs-Cookie · 401 E-Mail oder Passwort falsch ·
    403 Konto noch nicht bestätigt.
    """
    try:
        user = service.authenticate(db, data.email, data.password)
    except service.AccountError as error:
        raise _http_error(error) from error
    _start_session(db, user, response)
    return user


@router.get("/me", response_model=UserResponse)
def me(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=config.SESSION_COOKIE_NAME),
):
    """Liefert das angemeldete Konto (für das Benutzermenü). 401, wenn niemand angemeldet ist."""
    user = service.get_user_by_session(db, session_token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nicht angemeldet.")
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=config.SESSION_COOKIE_NAME),
):
    """Meldet ab: Sitzung löschen und Cookie im Browser entfernen."""
    service.delete_session(db, session_token)
    response.delete_cookie(config.SESSION_COOKIE_NAME)
