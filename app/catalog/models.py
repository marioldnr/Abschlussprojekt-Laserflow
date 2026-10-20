"""Datenbank-Tabellen des Moduls catalog.

Tabellen:
    products        Produkte, die graviert werden können
    product_images  Fotos eines Produkts für den Katalog
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    """Ein Produkt im Katalog (z. B. Holzbrett, Schlüsselanhänger).

    Bewusste Entscheidungen:
        - Preise in Cent als Ganzzahl (``price_cent``), damit es keine Rundungsfehler gibt.
        - Alle Maße in Millimetern.
        - Dateien (CAD-Vorlage, Laserprogramm) liegen im Dateisystem, hier steht nur der Pfad.
        - Produkte werden nicht gelöscht, sondern ausgeblendet (``is_hidden``),
          damit alte Bestellungen weiter auf sie zeigen können.
        - ``product_type`` und ``laser_settings`` sind noch offen gehalten, weil die
          Infos zur Maschine erst später kommen.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    width_mm: Mapped[int]
    height_mm: Mapped[int]
    depth_mm: Mapped[int | None]
    price_cent: Mapped[int]
    product_type: Mapped[str | None] = mapped_column(String(50))
    engraving_width_mm: Mapped[int | None]
    engraving_height_mm: Mapped[int | None]
    cad_template_path: Mapped[str | None] = mapped_column(String(500))
    laser_program_path: Mapped[str | None] = mapped_column(String(500))
    laser_settings: Mapped[str | None] = mapped_column(Text)
    is_sold_out: Mapped[bool] = mapped_column(default=False)
    is_hidden: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", order_by="ProductImage.sort_order"
    )


class ProductImage(Base):
    """Ein Foto eines Produkts. ``sort_order`` bestimmt die Reihenfolge (0 = Titelbild)."""

    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    file_path: Mapped[str] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(default=0)

    product: Mapped["Product"] = relationship(back_populates="images")
