"""Endpunkte für "Mein Konto" (US10) unter /api/account. Alle nur für angemeldete Kunden.

    GET    /api/account                    alle Daten                                 200
    PUT    /api/account/profile            Name und Adresse ändern                    200 / 422
    PUT    /api/account/password           Passwort ändern                            204 / 422
    POST   /api/account/email              neue E-Mail anfordern (Code an neue Adr.)  202 / 422
    POST   /api/account/email/verify       neue E-Mail mit Code bestätigen            200 / 400 / 409 / 410 / 429
    POST   /api/account/email/resend-code  neuen Code an die neue Adresse             204 / 409
    DELETE /api/account/email              offene Änderung abbrechen                  204
    GET    /api/account/avatar             Profilbild (Bilddatei)                     200 / 404
    PUT    /api/account/avatar             Profilbild hochladen (Bild als Body)       200 / 422
    DELETE /api/account/avatar             Profilbild entfernen                       204
    POST   /api/account/delete             Konto löschen (= deaktivieren)             204 / 422

Ohne Anmeldung antworten alle mit 401 (siehe dependencies.get_current_user).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import config
from app.accounts import account_service, service
from app.accounts.dependencies import get_current_user, get_session_token
from app.accounts.models import User
from app.accounts.schemas import (
    AvatarResponse,
    CodeRequest,
    EmailChangeRequest,
    PasswordChange,
    PasswordConfirm,
    PendingEmailResponse,
    ProfileResponse,
    ProfileUpdate,
    avatar_url_for,
)
from app.database import get_db

router = APIRouter(prefix="/api/account", tags=["Mein Konto"])


def _http_error(error: service.AccountError) -> HTTPException:
    """Wandelt einen Fehler aus dem Service in eine HTTP-Antwort {"detail": ...} um."""
    return HTTPException(status_code=error.status_code, detail=error.detail)


@router.get("", response_model=ProfileResponse)
def get_account(user: User = Depends(get_current_user)):
    """Alle Daten des angemeldeten Kunden für die Seite "Mein Konto"."""
    return account_service.get_profile(user)


@router.put("/profile", response_model=ProfileResponse)
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ändert Name und Lieferadresse. 422 mit Meldung pro Feld bei ungültigen Eingaben."""
    try:
        account_service.update_profile(db, user, data.model_dump())
    except service.AccountError as error:
        raise _http_error(error) from error
    return account_service.get_profile(user)


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    session_token: str | None = Depends(get_session_token),
):
    """Ändert das Passwort. Andere Sitzungen werden beendet, diese bleibt angemeldet."""
    try:
        account_service.change_password(db, user, data.current_password, data.new_password, keep_token=session_token)
    except service.AccountError as error:
        raise _http_error(error) from error


@router.post("/email", status_code=status.HTTP_202_ACCEPTED, response_model=PendingEmailResponse)
def request_email_change(data: EmailChangeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Schickt einen Code an die neue Adresse. 202 = angenommen, aber erst nach dem Code gültig."""
    try:
        email = account_service.request_email_change(db, user, data.new_email, data.password)
    except service.AccountError as error:
        raise _http_error(error) from error
    return PendingEmailResponse(pending_email=email)


@router.post("/email/verify", response_model=ProfileResponse)
def confirm_email_change(data: CodeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Bestätigt die neue E-Mail-Adresse mit dem Code."""
    try:
        account_service.confirm_email_change(db, user, data.code)
    except service.AccountError as error:
        raise _http_error(error) from error
    return account_service.get_profile(user)


@router.post("/email/resend-code", status_code=status.HTTP_204_NO_CONTENT)
def resend_email_change_code(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Neuer Code an die neue Adresse."""
    try:
        account_service.resend_email_change_code(db, user)
    except service.AccountError as error:
        raise _http_error(error) from error


@router.delete("/email", status_code=status.HTTP_204_NO_CONTENT)
def cancel_email_change(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Bricht die Änderung ab, die alte Adresse bleibt."""
    account_service.cancel_email_change(db, user)


@router.get("/avatar")
def get_avatar(user: User = Depends(get_current_user)):
    """Liefert das eigene Profilbild als Bilddatei. 404, wenn es keins gibt."""
    path = account_service.avatar_file(user)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kein Profilbild vorhanden.")
    return FileResponse(path)


@router.put("/avatar", response_model=AvatarResponse)
async def upload_avatar(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Speichert ein neues Profilbild.

    Das Bild kommt direkt als Body (nicht als Formular). So braucht FastAPI kein
    Zusatzpaket (python-multipart). Ist die Datei laut Content-Length zu groß, wird
    sie gar nicht erst gelesen.
    """
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > config.AVATAR_MAX_BYTES:
        raise _http_error(service.FieldValidationError({"avatar": account_service.MSG_AVATAR_SIZE}))
    content = await request.body()
    try:
        account_service.save_avatar(db, user, content)
    except service.AccountError as error:
        raise _http_error(error) from error
    return AvatarResponse(avatar_url=avatar_url_for(user.avatar_path))


@router.delete("/avatar", status_code=status.HTTP_204_NO_CONTENT)
def remove_avatar(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Entfernt das Profilbild."""
    account_service.remove_avatar(db, user)


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    data: PasswordConfirm,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Löscht das Konto (deaktivieren, abmelden). Bestätigt wird mit dem Passwort.

    POST statt DELETE, weil ein Body (das Passwort) mitgeschickt wird.
    """
    try:
        account_service.delete_account(db, user, data.password)
    except service.AccountError as error:
        raise _http_error(error) from error
    response.delete_cookie(config.SESSION_COOKIE_NAME)
