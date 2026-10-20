"""Datenbank-Tabellen des Moduls production.

Tabellen:
    production_jobs   ein Produktionsauftrag pro Bestellung
    production_files  die laserfertigen Dateien eines Auftrags

Hinweis: Die Produktion wird erst in einem späteren Sprint umgesetzt. Die Tabellen
stehen schon hier, damit das Datenmodell vollständig ist.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductionJob(Base):
    """Produktionsauftrag zu einer Bestellung (höchstens einer pro Bestellung).

    Erlaubte Werte für status: "pending", "ready", "done", "failed"
    """

    __tablename__ = "production_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    package_path: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    files: Mapped[list["ProductionFile"]] = relationship(back_populates="job")


class ProductionFile(Base):
    """Eine laserfertige Datei (SVG oder DXF). ``sheet_number`` = Nummer der Platte."""

    __tablename__ = "production_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    production_job_id: Mapped[int] = mapped_column(ForeignKey("production_jobs.id"))
    file_path: Mapped[str] = mapped_column(String(500))
    file_format: Mapped[str] = mapped_column(String(10))
    sheet_number: Mapped[int] = mapped_column(default=1)

    job: Mapped["ProductionJob"] = relationship(back_populates="files")
