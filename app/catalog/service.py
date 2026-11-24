"""Logik für den Produktkatalog (US01): Produkte lesen, ausverkauft markieren, anlegen.

Ablauf:
    list_visible_products():  alle Produkte, die Kunden sehen dürfen.
    get_visible_product():    ein Produkt über seine ID, ausgeblendete zählen als "nicht da".
    list_all_products():      alle Produkte inkl. ausgeblendete, für die Verwaltung (Mitarbeiter).
    get_product():            ein Produkt über seine ID, auch ausgeblendete (Verwaltung).
    set_sold_out():           Mitarbeiter markiert ein Produkt als ausverkauft oder wieder verfügbar.
    set_hidden():             Mitarbeiter blendet ein Produkt aus oder wieder ein (Flag, kein Löschen).
    create_product():         legt ein Produkt mit Bildern an (Grundlage für Seed und US14).

Bewusste Entscheidungen:
    - Die Funktionen kennen kein HTTP. Den Status-Code liefert jede Fehlerklasse selbst
      (``status_code``), der Router gibt ihn nur weiter. Das ist derselbe Aufbau wie in
      app/accounts/service.py und employee_service.py.
    - Ausgeblendete Produkte (``is_hidden``) werden nie gelöscht, sondern von allen
      Lesewegen ferngehalten. So zeigen alte Bestellungen weiter auf sie.
    - Die Produktart ist eine Textspalte ohne Datenbank-Enum. Die erlaubten Werte stehen
      hier, damit neue Arten ohne Migration dazukommen. Geprüft wird im Service (check_product_type).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.models import Product, ProductImage

# Produktarten (Text in der Spalte product_type).
PRODUCT_TYPE_CUSTOMER_IMAGE = "customer_image"  # Kunde lädt eigenes Bild hoch (US04)
PRODUCT_TYPE_FINISHED = "finished"  # fertiges Produkt aus dem Sortiment
PRODUCT_TYPES = (PRODUCT_TYPE_CUSTOMER_IMAGE, PRODUCT_TYPE_FINISHED)

MSG_PRODUCT_NOT_FOUND = "Dieses Produkt gibt es nicht."
MSG_PRODUCT_TYPE_INVALID = "Unbekannte Produktart."


class CatalogError(Exception):
    """Basis für erwartete Fehler im Katalog.

    Attributes:
        status_code: passender HTTP-Status (der Router gibt ihn weiter).
        detail: Meldung für die Anzeige im Frontend.
    """

    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class ProductNotFoundError(CatalogError):
    """Es gibt kein sichtbares Produkt mit dieser ID (404).

    Ausgeblendete Produkte melden dasselbe wie nicht vorhandene, damit man nicht
    erfährt, dass es sie gibt.
    """

    status_code = 404


class InvalidProductTypeError(CatalogError):
    """Die Produktart ist nicht bekannt (422)."""

    status_code = 422


def list_visible_products(db: Session) -> list[Product]:
    """Liefert alle sichtbaren Produkte, sortiert nach ID.

    Args:
        db: Datenbank-Session.

    Returns:
        Liste der Produkte mit ``is_hidden == False`` (kann leer sein).
    """
    return list(db.scalars(select(Product).where(Product.is_hidden.is_(False)).order_by(Product.id)))


def get_visible_product(db: Session, product_id: int) -> Product:
    """Holt ein sichtbares Produkt über seine ID.

    Args:
        db: Datenbank-Session.
        product_id: ID des Produkts.

    Returns:
        das Produkt.

    Raises:
        ProductNotFoundError: die ID gibt es nicht oder das Produkt ist ausgeblendet (404).
    """
    product = db.get(Product, product_id)
    if product is None or product.is_hidden:
        raise ProductNotFoundError(MSG_PRODUCT_NOT_FOUND)
    return product


def list_all_products(db: Session) -> list[Product]:
    """Liefert alle Produkte, auch die ausgeblendeten, sortiert nach ID.

    Für die Verwaltung (US14): Mitarbeiter sehen ausgeblendete Produkte, um sie wieder
    einzublenden. Kunden bekommen diese Liste nie (dort gilt list_visible_products).

    Args:
        db: Datenbank-Session.

    Returns:
        Liste aller Produkte (kann leer sein).
    """
    return list(db.scalars(select(Product).order_by(Product.id)))


def get_product(db: Session, product_id: int) -> Product:
    """Holt ein Produkt über seine ID, auch wenn es ausgeblendet ist.

    Anders als get_visible_product gibt es hier keine Sichtbarkeitsprüfung. Die Funktion
    ist nur für Mitarbeiter gedacht. Kunden-Endpunkte müssen get_visible_product benutzen.

    Args:
        db: Datenbank-Session.
        product_id: ID des Produkts.

    Returns:
        das Produkt, sichtbar oder ausgeblendet.

    Raises:
        ProductNotFoundError: die ID gibt es nicht (404).
    """
    product = db.get(Product, product_id)
    if product is None:
        raise ProductNotFoundError(MSG_PRODUCT_NOT_FOUND)
    return product


def set_sold_out(db: Session, product_id: int, is_sold_out: bool) -> Product:
    """Markiert ein Produkt als ausverkauft oder wieder verfügbar (US14 folgt mit Oberfläche).

    Auch ausgeblendete Produkte dürfen markiert werden. Die Mitarbeiter-Seite zeigt sie
    ja gerade, damit man sie wieder einblenden kann. Der Status ist unabhängig von der
    Sichtbarkeit: Ein ausgeblendetes Produkt bleibt ausverkauft, wenn es wieder eingeblendet wird.

    Args:
        db: Datenbank-Session.
        product_id: ID des Produkts.
        is_sold_out: True = ausverkauft, False = wieder verfügbar.

    Returns:
        das geänderte Produkt.

    Raises:
        ProductNotFoundError: die ID gibt es nicht (404).
    """
    product = get_product(db, product_id)
    product.is_sold_out = is_sold_out
    db.commit()
    db.refresh(product)
    return product


def set_hidden(db: Session, product_id: int, is_hidden: bool) -> Product:
    """Blendet ein Produkt im Katalog aus oder wieder ein (US14).

    Ausblenden ist das "Löschen" dieses Projekts: Es wird nur das Flag ``is_hidden`` gesetzt.
    Das Produkt bleibt in der Datenbank, damit alte Bestellungen weiter auf es zeigen.
    Wieder einblenden ist jederzeit möglich.

    Args:
        db: Datenbank-Session.
        product_id: ID des Produkts.
        is_hidden: True = ausblenden, False = wieder einblenden.

    Returns:
        das geänderte Produkt.

    Raises:
        ProductNotFoundError: die ID gibt es nicht (404).
    """
    product = get_product(db, product_id)
    product.is_hidden = is_hidden
    db.commit()
    db.refresh(product)
    return product


def check_product_type(value: str) -> str:
    """Prüft, ob die Produktart erlaubt ist.

    Args:
        value: Produktart, z. B. "finished".

    Returns:
        die unveränderte Produktart.

    Raises:
        InvalidProductTypeError: die Produktart steht nicht in PRODUCT_TYPES (422).
    """
    if value not in PRODUCT_TYPES:
        raise InvalidProductTypeError(MSG_PRODUCT_TYPE_INVALID)
    return value


def create_product(
    db: Session,
    *,
    name: str,
    description: str,
    width_mm: int,
    height_mm: int,
    depth_mm: int | None,
    price_cent: int,
    product_type: str,
    engraving_width_mm: int | None = None,
    engraving_height_mm: int | None = None,
    image_paths: tuple[str, ...] | list[str] = (),
) -> Product:
    """Legt ein Produkt mit seinen Bildern an.

    Wird vom Seed (scripts/seed_db.py) und von den Tests benutzt. Später kommt darüber
    die Produktverwaltung (US14) dazu.

    Args:
        db: Datenbank-Session.
        name: Anzeigename.
        description: ausführlicher Text. Der erste Satz dient als Kurzbeschreibung.
        width_mm, height_mm, depth_mm: Maße in Millimetern (Tiefe darf fehlen).
        price_cent: Preis in Cent (ganze Zahl, keine Rundungsfehler).
        product_type: "customer_image" oder "finished".
        engraving_width_mm, engraving_height_mm: Gravurbereich in mm, falls es einen gibt.
        image_paths: Dateipfade der Bilder. Die Reihenfolge bestimmt ``sort_order``
            (0 = Titelbild). Nur der Pfad kommt in die Datenbank, die Datei liegt im Dateisystem.

    Returns:
        das neue Produkt.

    Raises:
        InvalidProductTypeError: die Produktart ist unbekannt (422). Es wird nichts angelegt.
    """
    check_product_type(product_type)
    product = Product(
        name=name,
        description=description,
        width_mm=width_mm,
        height_mm=height_mm,
        depth_mm=depth_mm,
        price_cent=price_cent,
        product_type=product_type,
        engraving_width_mm=engraving_width_mm,
        engraving_height_mm=engraving_height_mm,
        images=[ProductImage(file_path=path, sort_order=index) for index, path in enumerate(image_paths)],
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
