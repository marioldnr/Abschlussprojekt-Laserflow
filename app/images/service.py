"""Logik des Moduls images: Kundenbilder hochladen und abrufen (US04).

Ablauf beim Hochladen (siehe upload_image):
    1. Produkt prüfen (muss existieren, sichtbar sein und einen Gravurbereich haben)
    2. Datei prüfen (nicht leer, höchstens 5 MB, JPEG oder PNG)
    3. Bildqualität prüfen (app/images/quality.py): Auflösung hart, Kontrast und Schärfe als Warnung
    4. Datei über app/storage.py speichern (Neon Object Storage oder lokal)
    5. Eintrag in customer_images mit Status "uploaded" und ggf. Warnungen anlegen
"""

import secrets
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app import storage
from app.accounts.models import User
from app.catalog.models import Product
from app.images import quality
from app.images.models import CustomerImage

# Höchstgröße laut Akzeptanzkriterium von US04. Genau 5 MB sind noch erlaubt.
MAX_BYTES = 5 * 1024 * 1024

MSG_EMPTY = "Die Datei ist leer."
MSG_SIZE = f"Das Bild darf höchstens {MAX_BYTES // (1024 * 1024)} MB groß sein."
MSG_TYPE = "Bitte wähle ein Bild im Format JPEG oder PNG."
MSG_PRODUCT_NOT_FOUND = "Dieses Produkt gibt es nicht."
MSG_IMAGE_NOT_FOUND = "Dieses Bild gibt es nicht."
MSG_NO_UPLOAD = quality.MSG_NO_ENGRAVING_AREA

# Trennzeichen, wenn mehrere Warnungen in der Spalte quality_warning stehen
WARNING_SEPARATOR = "; "

STATUS_UPLOADED = "uploaded"


# --------------------------------------------------------------------------- Fehler


class ImageError(Exception):
    """Basis für alle erwarteten Fehler in diesem Modul.

    Attributes:
        status_code: passender HTTP-Status (der Router gibt ihn weiter).
        detail: Meldung für das Frontend (Text oder Liste von Feldfehlern).
    """

    status_code = 400

    def __init__(self, detail):
        super().__init__(detail)
        self.detail = detail


class ImageValidationError(ImageError):
    """Die hochgeladene Datei ist ungültig (422).

    ``detail`` hat dasselbe Format wie bei den Formularen im Modul accounts:
    [{"loc": ["body", "image"], "msg": "<meldung>"}]. So zeigt das Frontend die Meldung
    an der gleichen Stelle wie alle anderen Feldfehler.
    """

    status_code = 422

    def __init__(self, message: str):
        super().__init__([{"loc": ["body", "image"], "msg": message}])
        self.message = message


class ProductNotFoundError(ImageError):
    """Das Produkt gibt es nicht oder es ist ausgeblendet (404)."""

    status_code = 404

    def __init__(self):
        super().__init__(MSG_PRODUCT_NOT_FOUND)


class ProductNotUploadableError(ImageError):
    """Das Produkt hat keinen Gravurbereich, ein Kundenbild ist dafür nicht möglich (404)."""

    status_code = 404

    def __init__(self):
        super().__init__(MSG_NO_UPLOAD)


class ImageNotFoundError(ImageError):
    """Das Bild gibt es nicht oder es gehört einem anderen Kunden (404)."""

    status_code = 404

    def __init__(self):
        super().__init__(MSG_IMAGE_NOT_FOUND)


# --------------------------------------------------------------------------- Prüfung


def detect_image_type(content: bytes) -> str | None:
    """Erkennt JPEG oder PNG an den ersten Bytes der Datei ("Magic Bytes").

    Warum nicht Dateiendung oder Content-Type: Beides schickt der Browser mit und lässt
    sich beliebig fälschen. Die ersten Bytes gehören zum Dateiformat selbst.

    Returns:
        "jpg" oder "png", sonst None.
    """
    if content.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    return None


def validate_file(content: bytes) -> str:
    """Prüft die Datei, bevor sie gespeichert wird (US04 Task 2).

    Reihenfolge: leer → zu groß → falscher Typ. Die Größe zuerst, damit eine riesige
    Datei nicht noch untersucht wird.

    Returns:
        Dateiendung für den Speicher-Schlüssel ("jpg" oder "png").

    Raises:
        ImageValidationError: Datei leer, größer als 5 MB oder kein JPEG/PNG.
    """
    if not content:
        raise ImageValidationError(MSG_EMPTY)
    if len(content) > MAX_BYTES:
        raise ImageValidationError(MSG_SIZE)
    extension = detect_image_type(content)
    if extension is None:
        raise ImageValidationError(MSG_TYPE)
    return extension


# --------------------------------------------------------------------------- Hochladen und abrufen


@dataclass
class UploadResult:
    """Ergebnis eines Uploads: der neue Datenbank-Eintrag und die Messwerte der Prüfung.

    ``quality.needs_upscale`` wird nicht gespeichert (keine eigene Spalte). US06 rechnet
    den Faktor beim Aufbereiten aus Bild und Produkt selbst neu aus.
    """

    image: CustomerImage
    quality: quality.QualityResult


def upload_image(db: Session, user: User, product_id: int, content: bytes) -> UploadResult:
    """Prüft und speichert ein Kundenbild für ein Produkt (US04 Task 1 bis 3).

    Die Datei kommt unverändert in den Bildspeicher, in der Datenbank steht nur der
    Schlüssel (z. B. ``customer-images/3-a1b2c3d4e5f60718.png``). Der Zufallsteil
    verhindert, dass zwei Uploads denselben Namen bekommen.
    Gespeichert wird erst, wenn alle harten Prüfungen bestanden sind. Warnungen
    (Kontrast, Schärfe) stehen danach in ``quality_warning``, getrennt mit "; ".

    Args:
        db: Datenbank-Session.
        user: angemeldetes Konto.
        product_id: Produkt, auf das graviert werden soll.
        content: Inhalt der Datei.

    Returns:
        UploadResult mit dem neuen Eintrag (Status "uploaded") und den Messwerten.

    Raises:
        ProductNotFoundError: Produkt fehlt oder ist ausgeblendet.
        ProductNotUploadableError: Produkt hat keinen Gravurbereich.
        ImageValidationError: Datei ungültig (siehe validate_file), nicht lesbar oder
            so klein, dass auch Hochskalieren nicht reicht (Meldung nennt die Mindestgröße).
    """
    product = db.get(Product, product_id)
    if product is None or product.is_hidden:
        raise ProductNotFoundError()
    try:
        quality.target_size(product.engraving_width_mm, product.engraving_height_mm)
    except quality.NoEngravingAreaError as error:
        raise ProductNotUploadableError() from error

    extension = validate_file(content)
    try:
        result = quality.check_quality(content, product.engraving_width_mm, product.engraving_height_mm)
    except (quality.ResolutionTooLowError, quality.UnreadableImageError) as error:
        raise ImageValidationError(error.message) from error

    key = f"customer-images/{user.id}-{secrets.token_hex(8)}.{extension}"
    storage.save_file(key, content)

    image = CustomerImage(
        user_id=user.id,
        product_id=product.id,
        original_path=key,
        status=STATUS_UPLOADED,
        quality_warning=WARNING_SEPARATOR.join(result.warnings) or None,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return UploadResult(image=image, quality=result)


def get_own_image(db: Session, user: User, image_id: int) -> CustomerImage:
    """Liefert ein Bild, aber nur, wenn es dem angemeldeten Kunden gehört.

    Warum 404 statt 403 bei fremden Bildern: So erfährt niemand, ob es ein Bild mit
    dieser Nummer überhaupt gibt.

    Raises:
        ImageNotFoundError: Bild fehlt oder gehört jemand anderem.
    """
    image = db.get(CustomerImage, image_id)
    if image is None or image.user_id != user.id:
        raise ImageNotFoundError()
    return image


def original_file(image: CustomerImage) -> tuple[bytes, str]:
    """Inhalt und Content-Type des Originalbilds.

    Raises:
        ImageNotFoundError: Die Datei fehlt im Bildspeicher.
    """
    content = storage.read_file(image.original_path)
    if content is None:
        raise ImageNotFoundError()
    return content, storage.content_type_for(image.original_path)
