"""Endpunkte für US01: Produktkatalog (/api/products).

    GET  /api/products                  alle sichtbaren Produkte          200
    GET  /api/products/manage           alle Produkte inkl. ausgeblendete (nur Mitarbeiter/Admin)
                                        200 / 401 / 403
    GET  /api/products/{product_id}     ein sichtbares Produkt            200 / 404
    PUT  /api/products/{product_id}/sold-out  ausverkauft markieren (nur Mitarbeiter/Admin)
                                        200 / 401 / 403 / 404 / 422
    PUT  /api/products/{product_id}/hidden    ausblenden / einblenden (nur Mitarbeiter/Admin)
                                        200 / 401 / 403 / 404 / 422

Der Katalog ist öffentlich lesbar, ohne Anmeldung. Alle Schreib- und Verwaltungs-Endpunkte
brauchen einen angemeldeten Mitarbeiter oder Admin; die Prüfung kommt aus
app/accounts/dependencies.py (require_employee).

Wichtig: GET /manage steht absichtlich VOR GET /{product_id}. Sonst würde FastAPI "manage"
als Produkt-ID lesen und mit 422 antworten.

Der Router macht nur HTTP: Daten annehmen, Service aufrufen, Antwort zurückgeben.
Die Logik steht in service.py.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.accounts.dependencies import require_employee
from app.accounts.models import User
from app.catalog import service
from app.catalog.schemas import HiddenRequest, ManagedProductResponse, ProductResponse, SoldOutRequest
from app.database import get_db

router = APIRouter(prefix="/api/products", tags=["Katalog"])


def _http_error(error: service.CatalogError) -> HTTPException:
    """Wandelt einen Fehler aus dem Service in eine HTTP-Antwort {"detail": ...} um."""
    return HTTPException(status_code=error.status_code, detail=error.detail)


@router.get("", response_model=list[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    """Liefert alle sichtbaren Produkte für den Katalog. Ohne Anmeldung."""
    return [ProductResponse.from_product(p) for p in service.list_visible_products(db)]


@router.get("/manage", response_model=list[ManagedProductResponse])
def list_managed_products(db: Session = Depends(get_db), employee: User = Depends(require_employee)):
    """Liefert alle Produkte inkl. ausgeblendete für die Verwaltung. Nur Mitarbeiter und Admins.

    Antworten: 200 · 401 nicht angemeldet · 403 Kunde.
    """
    return [ManagedProductResponse.from_product(p) for p in service.list_all_products(db)]


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Liefert ein sichtbares Produkt. 404, wenn es die ID nicht gibt oder es ausgeblendet ist."""
    try:
        return ProductResponse.from_product(service.get_visible_product(db, product_id))
    except service.CatalogError as error:
        raise _http_error(error) from error


@router.put("/{product_id}/sold-out", response_model=ManagedProductResponse)
def set_sold_out(
    product_id: int,
    data: SoldOutRequest,
    db: Session = Depends(get_db),
    employee: User = Depends(require_employee),
):
    """Markiert ein Produkt als ausverkauft oder wieder verfügbar. Auch ausgeblendete Produkte.

    Antworten: 200 geändert · 401 nicht angemeldet · 403 Kunde · 404 unbekannte ID ·
    422 Feld is_sold_out fehlt oder ist kein Wahrheitswert.
    """
    try:
        return ManagedProductResponse.from_product(service.set_sold_out(db, product_id, data.is_sold_out))
    except service.CatalogError as error:
        raise _http_error(error) from error


@router.put("/{product_id}/hidden", response_model=ManagedProductResponse)
def set_hidden(
    product_id: int,
    data: HiddenRequest,
    db: Session = Depends(get_db),
    employee: User = Depends(require_employee),
):
    """Blendet ein Produkt aus (is_hidden true) oder wieder ein (false). Nur Mitarbeiter und Admins.

    Ausblenden ist kein Löschen, nur ein Flag. Die Antwort ist das geänderte Produkt.

    Antworten: 200 geändert · 401 nicht angemeldet · 403 Kunde · 404 unbekannte ID ·
    422 Feld is_hidden fehlt oder ist kein Wahrheitswert.
    """
    try:
        return ManagedProductResponse.from_product(service.set_hidden(db, product_id, data.is_hidden))
    except service.CatalogError as error:
        raise _http_error(error) from error
