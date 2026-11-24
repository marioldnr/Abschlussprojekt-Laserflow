"""Qualitätsprüfung für Kundenbilder (US04 Task 3).

Prüft, ob ein hochgeladenes Bild für die Gravur taugt:

    1. Auflösung (hart): Reicht die Pixelzahl für den Gravurbereich des Produkts?
       Fehlt höchstens Faktor 4, wird später per KI hochskaliert (US06).
       Fehlt mehr, wird das Bild abgelehnt.
    2. Kontrast und Schärfe (weich): Bei schwachen Werten gibt es nur eine Warnung.

Das Modul kennt weder Datenbank noch Bildspeicher. Es bekommt die Bild-Bytes und die
Maße des Gravurbereichs und gibt ein Ergebnis zurück. Aufgerufen wird es aus
app/images/service.py beim Upload.

Werte abgestimmt mit Mario am 24.11.2026 (KI-Plan vom 17.11., Grenzwerte mit Testbildern geprüft).
"""

import io
import math
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

# --------------------------------------------------------------------------- Grenzwerte

PIXELS_PER_MM = 10  # Laser-Auflösung, ca. 254 dpi
MARGIN_MM = 1  # Rand pro Seite, der nicht graviert wird
MAX_UPSCALE_FACTOR = 4  # so viel kann die KI-Hochskalierung (US06) ausgleichen
MIN_CONTRAST = 25.0  # Standardabweichung der Grauwerte (0–255); darunter: Warnung
MIN_SHARPNESS = 30.0  # Varianz des Laplace-Filters bei Zielgröße; darunter: Warnung

MSG_NO_ENGRAVING_AREA = "Für dieses Produkt ist kein Bild-Upload möglich."
MSG_UNREADABLE = "Das Bild konnte nicht gelesen werden. Bitte wähle eine andere Datei."
MSG_TOO_SMALL = "Das Bild ist zu klein für dieses Produkt. Es braucht mindestens {width} × {height} Pixel."
WARNING_CONTRAST = "Das Bild ist sehr kontrastarm. Die Gravur kann blass wirken."
WARNING_SHARPNESS = "Das Bild wirkt unscharf. Die Gravur kann verschwommen aussehen."


# --------------------------------------------------------------------------- Fehler


class QualityError(Exception):
    """Basis für Fehler der Qualitätsprüfung. ``message`` ist für die Anzeige gedacht."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NoEngravingAreaError(QualityError):
    """Das Produkt hat keinen (brauchbaren) Gravurbereich, also ist kein Kundenbild möglich."""

    def __init__(self):
        super().__init__(MSG_NO_ENGRAVING_AREA)


class UnreadableImageError(QualityError):
    """Pillow kann die Datei nicht öffnen (kaputt oder übergroß)."""

    def __init__(self):
        super().__init__(MSG_UNREADABLE)


class ResolutionTooLowError(QualityError):
    """Es fehlt mehr als Faktor 4. Auch Hochskalieren reicht nicht.

    Attributes:
        min_width, min_height: Mindestgröße in Pixeln, die der Kunde braucht.
    """

    def __init__(self, min_width: int, min_height: int):
        super().__init__(MSG_TOO_SMALL.format(width=min_width, height=min_height))
        self.min_width = min_width
        self.min_height = min_height


# --------------------------------------------------------------------------- Ergebnis


@dataclass
class QualityResult:
    """Ergebnis der Prüfung eines Bildes, das nicht abgelehnt wurde.

    Attributes:
        width, height: Größe des Bildes in Pixeln (nach Drehung laut EXIF).
        target_width, target_height: Pixel, die der Gravurbereich braucht.
        factor: um so viel müsste das Bild vergrößert werden (≤ 1 heißt: reicht schon).
        needs_upscale: True, wenn ``factor`` > 1 (US06 skaliert hoch).
        contrast, sharpness: Messwerte (zum Nachjustieren der Grenzwerte).
        warnings: Hinweise für den Kunden, leer wenn alles passt.
    """

    width: int
    height: int
    target_width: int
    target_height: int
    factor: float
    needs_upscale: bool
    contrast: float
    sharpness: float
    warnings: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- Einzelne Schritte


def target_size(engraving_width_mm: int | None, engraving_height_mm: int | None) -> tuple[int, int]:
    """Pixel, die ein Bild für den Gravurbereich mindestens haben soll.

    Formel: (Gravurbereich − 2 × Rand) × Pixel pro mm. Beispiel 80 × 60 mm → 780 × 580 Pixel.

    Raises:
        NoEngravingAreaError: Maße fehlen oder sind nach Abzug des Randes nicht größer als 0.
    """
    if not engraving_width_mm or not engraving_height_mm:
        raise NoEngravingAreaError()
    width = (engraving_width_mm - 2 * MARGIN_MM) * PIXELS_PER_MM
    height = (engraving_height_mm - 2 * MARGIN_MM) * PIXELS_PER_MM
    if width <= 0 or height <= 0:
        raise NoEngravingAreaError()
    return width, height


def upscale_factor(width: int, height: int, target_width: int, target_height: int) -> float:
    """Um wie viel das Bild vergrößert werden müsste, damit es den Gravurbereich füllt.

    Maßgeblich ist die knappere Seite (größerer Wert), weil das Bild den ganzen Bereich
    abdecken soll.
    """
    return max(target_width / width, target_height / height)


def minimum_size(target_width: int, target_height: int) -> tuple[int, int]:
    """Kleinste Größe, die mit Hochskalieren um Faktor 4 noch reicht (aufgerundet)."""
    return math.ceil(target_width / MAX_UPSCALE_FACTOR), math.ceil(target_height / MAX_UPSCALE_FACTOR)


def open_image(content: bytes) -> Image.Image:
    """Öffnet die Bild-Bytes und dreht das Bild so, wie es aufgenommen wurde.

    Handyfotos speichern die Drehung oft nur als EXIF-Angabe. Ohne ``exif_transpose``
    wären Breite und Höhe bei Hochformat-Fotos vertauscht.

    Raises:
        UnreadableImageError: Datei kaputt oder so groß, dass Pillow sie als
            „Dekompressionsbombe“ ablehnt (Schutz vor Speicherüberlauf).
    """
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
        return ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise UnreadableImageError() from error


def to_gray_at_target(image: Image.Image, target_width: int, target_height: int) -> np.ndarray:
    """Graustufen-Bild, so skaliert, dass es genau in die Zielgröße passt (Seitenverhältnis bleibt).

    Warum skalieren: Die Schärfe (Laplace-Varianz) hängt stark von der Bildgröße ab.
    Dasselbe scharfe Foto hatte im Test bei 512 px den Wert 1132, bei 2048 px nur 10.
    Gemessen bei Zielgröße sind die Werte vergleichbar, egal wie groß das Original ist.
    """
    scale = min(target_width / image.width, target_height / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    gray = image.convert("L").resize(size, Image.LANCZOS)
    return np.asarray(gray, dtype=np.float64)


def measure_contrast(gray: np.ndarray) -> float:
    """Kontrast = Standardabweichung der Grauwerte (0 = einfarbig, ca. 128 = nur Schwarz und Weiß)."""
    return float(gray.std())


def measure_sharpness(gray: np.ndarray) -> float:
    """Schärfe = Varianz des Laplace-Filters.

    Der Laplace-Filter reagiert auf Kanten: Für jeden Pixel wird 4 × Pixel minus die vier
    Nachbarn gerechnet. Scharfe Bilder haben viele starke Kanten, die Werte schwanken stark
    (große Varianz). Bei unscharfen Bildern sind die Übergänge weich, die Varianz ist klein.
    Bilder unter 3 × 3 Pixeln haben keine Kanten zum Messen, dann ist das Ergebnis 0.
    """
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    laplace = (
        gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:] - 4 * gray[1:-1, 1:-1]
    )
    return float(laplace.var())


# --------------------------------------------------------------------------- Gesamtprüfung


def check_quality(content: bytes, engraving_width_mm: int | None, engraving_height_mm: int | None) -> QualityResult:
    """Prüft ein Bild für einen Gravurbereich.

    Ablauf: Zielgröße bestimmen → Bild öffnen → Faktor prüfen (hart) → Kontrast und
    Schärfe messen (weich).

    Args:
        content: Bild-Bytes (Typ und Größe der Datei sind vorher schon geprüft).
        engraving_width_mm, engraving_height_mm: Gravurbereich des Produkts.

    Returns:
        QualityResult mit Messwerten und Warnungen.

    Raises:
        NoEngravingAreaError: Produkt hat keinen Gravurbereich.
        UnreadableImageError: Bild lässt sich nicht öffnen.
        ResolutionTooLowError: Es fehlt mehr als Faktor 4 (Meldung nennt die Mindestgröße).
    """
    target_width, target_height = target_size(engraving_width_mm, engraving_height_mm)
    image = open_image(content)

    factor = upscale_factor(image.width, image.height, target_width, target_height)
    if factor > MAX_UPSCALE_FACTOR:
        raise ResolutionTooLowError(*minimum_size(target_width, target_height))

    gray = to_gray_at_target(image, target_width, target_height)
    contrast = measure_contrast(gray)
    sharpness = measure_sharpness(gray)

    warnings = []
    if contrast < MIN_CONTRAST:
        warnings.append(WARNING_CONTRAST)
    if sharpness < MIN_SHARPNESS:
        warnings.append(WARNING_SHARPNESS)

    return QualityResult(
        width=image.width,
        height=image.height,
        target_width=target_width,
        target_height=target_height,
        factor=factor,
        needs_upscale=factor > 1,
        contrast=contrast,
        sharpness=sharpness,
        warnings=warnings,
    )
