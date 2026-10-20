"""Datenbank-Tabellen des Moduls images.

Tabellen:
    customer_images  Bilder, die Kunden für eine Gravur hochladen
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CustomerImage(Base):
    """Ein hochgeladenes Kundenbild mit seinen aufbereiteten Varianten.

    Ablauf: Original hochladen → Hintergrund entfernen (rembg) → für die Gravur
    aufbereiten. Jede Stufe ist eine eigene Datei, hier stehen nur die Pfade.

    Erlaubte Werte (als Text gespeichert, Prüfung im Service):
        chosen_variant: "original", "background_removed", "processed"
        status:         "uploaded", "processing", "ready", "failed"
    """

    __tablename__ = "customer_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    original_path: Mapped[str] = mapped_column(String(500))
    background_removed_path: Mapped[str | None] = mapped_column(String(500))
    processed_path: Mapped[str | None] = mapped_column(String(500))
    chosen_variant: Mapped[str | None] = mapped_column(String(30))
    was_upscaled: Mapped[bool] = mapped_column(default=False)
    quality_warning: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
