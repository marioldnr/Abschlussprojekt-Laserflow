"""Antwortformate des Moduls images (was die API zurückgibt)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field


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

    @computed_field
    @property
    def original_url(self) -> str:
        """Adresse, unter der der Kunde sein Originalbild abrufen kann."""
        return f"/api/images/{self.id}/original"
