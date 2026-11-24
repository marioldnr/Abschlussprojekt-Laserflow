"""Tests für app/images/quality.py (US04 Task 3): Auflösung, Kontrast und Schärfe.

Die Testbilder werden hier mit Pillow und NumPy erzeugt (keine Dateien im Repo).
Gravurbereich in allen Tests: 80 × 60 mm → Zielgröße 780 × 580 Pixel (wie die Demo-Gravurplatte).
"""

import io

import numpy as np
import pytest
from PIL import Image, ImageFilter

from app.images import quality

W_MM, H_MM = 80, 60
TARGET = (780, 580)


def to_bytes(image: Image.Image, fmt: str = "PNG", **kwargs) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


def noise(width: int, height: int, low: int = 0, high: int = 255, seed: int = 1) -> Image.Image:
    """Zufallsmuster: viele harte Kanten, also scharf. Mit kleinem Bereich (low/high) kontrastarm."""
    rng = np.random.default_rng(seed)
    return Image.fromarray(rng.integers(low, high + 1, size=(height, width), dtype=np.uint8))


def checkerboard(width: int, height: int, square: int = 40) -> Image.Image:
    """Schwarz-weißes Schachbrett: hoher Kontrast, klare Kanten."""
    y, x = np.indices((height, width))
    return Image.fromarray((((x // square + y // square) % 2) * 255).astype(np.uint8))


# --------------------------------------------------------------------------- Zielgröße


def test_target_size_example_from_plan():
    assert quality.target_size(80, 60) == (780, 580)


@pytest.mark.parametrize(("width_mm", "height_mm"), [(None, 60), (80, None), (None, None), (0, 60), (2, 60), (80, 1)])
def test_missing_or_too_small_engraving_area_is_rejected(width_mm, height_mm):
    with pytest.raises(quality.NoEngravingAreaError) as error:
        quality.target_size(width_mm, height_mm)
    assert error.value.message == "Für dieses Produkt ist kein Bild-Upload möglich."


def test_minimum_size_rounds_up():
    assert quality.minimum_size(780, 580) == (195, 145)
    assert quality.minimum_size(781, 581) == (196, 146)


# --------------------------------------------------------------------------- Auflösung (hart)


def test_exact_target_size_needs_no_upscale():
    result = quality.check_quality(to_bytes(noise(*TARGET)), W_MM, H_MM)
    assert result.factor == 1
    assert result.needs_upscale is False
    assert (result.target_width, result.target_height) == TARGET


def test_larger_image_needs_no_upscale():
    result = quality.check_quality(to_bytes(noise(2000, 1500)), W_MM, H_MM)
    assert result.factor < 1
    assert result.needs_upscale is False


def test_half_size_needs_upscale():
    result = quality.check_quality(to_bytes(noise(390, 290)), W_MM, H_MM)
    assert result.factor == pytest.approx(2)
    assert result.needs_upscale is True


def test_exactly_factor_4_is_still_accepted():
    result = quality.check_quality(to_bytes(noise(195, 145)), W_MM, H_MM)
    assert result.factor == pytest.approx(4)
    assert result.needs_upscale is True


def test_more_than_factor_4_is_rejected_with_minimum_size():
    with pytest.raises(quality.ResolutionTooLowError) as error:
        quality.check_quality(to_bytes(noise(194, 145)), W_MM, H_MM)
    assert (error.value.min_width, error.value.min_height) == (195, 145)
    assert error.value.message == "Das Bild ist zu klein für dieses Produkt. Es braucht mindestens 195 × 145 Pixel."


def test_shorter_side_decides():
    """Breit genug, aber zu niedrig: Die knappere Seite bestimmt den Faktor."""
    with pytest.raises(quality.ResolutionTooLowError):
        quality.check_quality(to_bytes(noise(2000, 100)), W_MM, H_MM)


def test_exif_rotation_is_respected():
    """Handyfoto im Hochformat gespeichert, laut EXIF gedreht: zählt mit den gedrehten Maßen."""
    stored = noise(580, 780).convert("RGB")
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: um 90° drehen
    result = quality.check_quality(to_bytes(stored, "JPEG", exif=exif), W_MM, H_MM)
    assert (result.width, result.height) == TARGET
    assert result.factor == pytest.approx(1)


def test_no_engraving_area_is_checked_before_opening_the_image():
    with pytest.raises(quality.NoEngravingAreaError):
        quality.check_quality(b"egal", None, None)


# --------------------------------------------------------------------------- Kontrast und Schärfe (weich)


def test_good_image_has_no_warnings():
    result = quality.check_quality(to_bytes(checkerboard(*TARGET)), W_MM, H_MM)
    assert result.warnings == []
    assert result.contrast >= quality.MIN_CONTRAST
    assert result.sharpness >= quality.MIN_SHARPNESS


def test_low_contrast_gives_only_contrast_warning():
    result = quality.check_quality(to_bytes(noise(*TARGET, low=118, high=138)), W_MM, H_MM)
    assert result.contrast < quality.MIN_CONTRAST
    assert result.warnings == [quality.WARNING_CONTRAST]


def test_blurred_image_gives_only_sharpness_warning():
    blurred = checkerboard(*TARGET, square=120).filter(ImageFilter.GaussianBlur(8))
    result = quality.check_quality(to_bytes(blurred), W_MM, H_MM)
    assert result.sharpness < quality.MIN_SHARPNESS
    assert result.warnings == [quality.WARNING_SHARPNESS]


def test_flat_gray_image_gives_both_warnings():
    result = quality.check_quality(to_bytes(Image.new("L", TARGET, 128)), W_MM, H_MM)
    assert result.contrast == 0
    assert result.sharpness == 0
    assert result.warnings == [quality.WARNING_CONTRAST, quality.WARNING_SHARPNESS]


def test_sharpness_does_not_depend_on_image_size():
    """Dasselbe Motiv klein und 4-mal so groß: Gemessen wird bei Zielgröße, also gleiche Größenordnung.

    Ohne das Skalieren wäre der Wert beim großen Bild deutlich kleiner (bei Fotos im Test
    sogar über 100-mal), weil sich die Kanten auf mehr Pixel verteilen. Ein scharfes
    Handyfoto würde dann fälschlich als unscharf gewarnt.
    """
    small = checkerboard(*TARGET)
    large = small.resize((TARGET[0] * 4, TARGET[1] * 4), Image.NEAREST)
    small_result = quality.check_quality(to_bytes(small), W_MM, H_MM)
    large_result = quality.check_quality(to_bytes(large), W_MM, H_MM)
    assert large_result.warnings == []
    assert small_result.sharpness / 2 < large_result.sharpness < small_result.sharpness * 2
    unscaled = quality.measure_sharpness(np.asarray(large, dtype=np.float64))
    assert unscaled < small_result.sharpness / 3


def test_transparent_png_can_be_checked():
    image = checkerboard(*TARGET).convert("RGBA")
    image.putalpha(128)
    result = quality.check_quality(to_bytes(image), W_MM, H_MM)
    assert result.factor == 1


def test_measure_functions_on_tiny_array():
    gray = np.array([[0.0, 255.0]])
    assert quality.measure_sharpness(gray) == 0.0
    assert quality.measure_contrast(gray) == pytest.approx(127.5)


# --------------------------------------------------------------------------- kaputte Dateien


def test_broken_file_is_rejected():
    broken = b"\x89PNG\r\n\x1a\n" + b"kaputt" * 20
    with pytest.raises(quality.UnreadableImageError) as error:
        quality.check_quality(broken, W_MM, H_MM)
    assert error.value.message == quality.MSG_UNREADABLE


def test_decompression_bomb_is_rejected(monkeypatch):
    """Riesige Pixelzahl in kleiner Datei: Pillow bricht ab, wir melden „nicht lesbar“."""
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)
    with pytest.raises(quality.UnreadableImageError):
        quality.check_quality(to_bytes(Image.new("L", (100, 100), 0)), W_MM, H_MM)
