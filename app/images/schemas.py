"""Antwortformate des Moduls images (was die API zurückgibt)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ImageResponse(BaseModel):
    """Ein Kundenbild, wie das Frontend es sieht.

    Der Speicher-Schlüssel (``original_path``) wird bewusst nicht ausgegeben. Das Frontend
    holt das Bild über ``original_url``, damit die Rechteprüfung immer greift.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    status: str
    created_at: datetime
    # Intern als Text mit "; " getrennt gespeichert, nach außen als Liste (quality_warnings)
    quality_warning: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def quality_warnings(self) -> list[str]:
        """Hinweise zu Kontrast und Schärfe. Leer, wenn alles passt."""
        return self.quality_warning.split("; ") if self.quality_warning else []

    @computed_field
    @property
    def original_url(self) -> str:
        """Adresse, unter der der Kunde sein Originalbild abrufen kann."""
        return f"/api/images/{self.id}/original"


class UploadResponse(ImageResponse):
    """Antwort direkt nach dem Upload: wie ImageResponse, dazu das Ergebnis der Auflösungsprüfung.

    ``needs_upscale`` gibt es nur hier, weil es nicht gespeichert wird (siehe service.UploadResult).
    """

    needs_upscale: bool
