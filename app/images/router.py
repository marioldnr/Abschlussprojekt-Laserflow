"""Endpunkte für Kundenbilder (US04) unter /api/images. Alle nur für Angemeldete.

    POST /api/images?product_id=<id>  Bild hochladen (Bild als Body)   201 / 404 / 422
    GET  /api/images/{id}             Daten zum eigenen Bild           200 / 404
    GET  /api/images/{id}/original    eigenes Originalbild (Datei)     200 / 404

Ohne Anmeldung antworten alle mit 401 (siehe dependencies.get_current_user).
Die Logik steht in app/images/service.py, hier wird nur weitergereicht.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.accounts.dependencies import get_current_user
from app.accounts.models import User
from app.database import get_db
from app.images import service
from app.images.schemas import ImageResponse

router = APIRouter(prefix="/api/images", tags=["Kundenbilder"])


def _http_error(error: service.ImageError) -> HTTPException:
    """Wandelt einen Fehler aus dem Service in eine HTTP-Antwort {"detail": ...} um."""
    return HTTPException(status_code=error.status_code, detail=error.detail)


@router.post("", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    request: Request,
    product_id: int = Query(..., description="Produkt, auf das graviert wird"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Nimmt ein Kundenbild für ein Produkt entgegen.

    Das Bild kommt direkt als Body (nicht als Formular), wie beim Profilbild. So braucht
    FastAPI kein Zusatzpaket (python-multipart). Ist die Datei laut Content-Length zu groß,
    wird sie gar nicht erst gelesen.
    """
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > service.MAX_BYTES:
        raise _http_error(service.ImageValidationError(service.MSG_SIZE))
    content = await request.body()
    try:
        image = service.upload_image(db, user, product_id, content)
    except service.ImageError as error:
        raise _http_error(error) from error
    return image


@router.get("/{image_id}", response_model=ImageResponse)
def get_image(image_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Daten zu einem eigenen Bild. Fremde Bilder: 404."""
    try:
        return service.get_own_image(db, user, image_id)
    except service.ImageError as error:
        raise _http_error(error) from error


@router.get("/{image_id}/original")
def get_original(image_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Das eigene Originalbild als Datei. Fremde Bilder oder fehlende Datei: 404."""
    try:
        image = service.get_own_image(db, user, image_id)
        content, content_type = service.original_file(image)
    except service.ImageError as error:
        raise _http_error(error) from error
    return Response(content=content, media_type=content_type)
