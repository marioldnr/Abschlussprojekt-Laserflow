"""Form der Daten für die Katalog-Endpunkte unter /api/products (US01).

Die Antwort ist eine Auswahl: Dateipfade zu CAD-Vorlage und Laserprogramm, Laser-Einstellungen,
das Ausblende-Flag und das Anlagedatum gehen bewusst nicht an Kunden. Dafür sorgt
``ProductResponse.from_product``, das nur die erlaubten Felder übernimmt.
"""

from pydantic import BaseModel

from app.catalog.models import Product


class ProductResponse(BaseModel):
    """Öffentliche Daten eines Produkts für Katalog und Produktseite.

    ``short_description`` ist der erste Satz der Beschreibung (siehe ``short_description_of``).
    ``images`` sind Dateipfade in der Reihenfolge ``sort_order``, das erste ist das Titelbild.
    """

    id: int
    name: str
    description: str | None
    short_description: str
    width_mm: int
    height_mm: int
    depth_mm: int | None
    price_cent: int
    product_type: str | None
    engraving_width_mm: int | None
    engraving_height_mm: int | None
    is_sold_out: bool
    images: list[str]

    @classmethod
    def from_product(cls, product: Product) -> "ProductResponse":
        """Baut die Antwort aus einem Produkt der Datenbank.

        Args:
            product: Produkt mit geladenen Bildern.

        Returns:
            die Antwort mit nur den öffentlichen Feldern.
        """
        return cls(
            id=product.id,
            name=product.name,
            description=product.description,
            short_description=short_description_of(product.description),
            width_mm=product.width_mm,
            height_mm=product.height_mm,
            depth_mm=product.depth_mm,
            price_cent=product.price_cent,
            product_type=product.product_type,
            engraving_width_mm=product.engraving_width_mm,
            engraving_height_mm=product.engraving_height_mm,
            is_sold_out=product.is_sold_out,
            images=[image.file_path for image in product.images],
        )


def short_description_of(description: str | None) -> str:
    """Liefert den ersten Satz einer Beschreibung als Kurzbeschreibung.

    Warum der erste Satz: Es gibt keine eigene Spalte für die Kurztext. Kacheln und der
    Kopf der Produktseite brauchen einen Satz, der Rest steht in der Beschreibung.

    Args:
        description: Beschreibung oder None.

    Returns:
        der Text bis einschließlich zum ersten Punkt, der von einem Leerzeichen gefolgt wird;
        ohne solchen Punkt die ganze Beschreibung; bei None ein leerer Text.
    """
    if not description:
        return ""
    end = description.find(". ")
    if end == -1:
        return description
    return description[: end + 1]


class ManagedProductResponse(ProductResponse):
    """Produkt für die Verwaltung (nur Mitarbeiter und Admins).

    Wie ProductResponse, zusätzlich ``is_hidden``, damit die Verwaltung ausgeblendete
    Produkte erkennt. Kunden bekommen dieses Format nie.
    """

    is_hidden: bool

    @classmethod
    def from_product(cls, product: Product) -> "ManagedProductResponse":
        """Baut die Verwaltungs-Antwort aus einem Produkt der Datenbank.

        Args:
            product: Produkt mit geladenen Bildern.

        Returns:
            die Antwort mit den öffentlichen Feldern plus ``is_hidden``.
        """
        public = ProductResponse.from_product(product).model_dump()
        return cls(**public, is_hidden=product.is_hidden)


class SoldOutRequest(BaseModel):
    """Körper der Anfrage PUT /api/products/{id}/sold-out."""

    is_sold_out: bool


class HiddenRequest(BaseModel):
    """Körper der Anfrage PUT /api/products/{id}/hidden. True blendet aus, False blendet ein."""

    is_hidden: bool
