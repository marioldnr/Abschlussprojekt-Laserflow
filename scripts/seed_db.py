"""Legt die gemeinsamen Startdaten in der eigenen, lokalen laserflow.db an.

Die Datenbank selbst kommt nie ins Repo. Jeder im Team startet dieses Skript einmal
(und nach jedem Löschen von laserflow.db erneut) und hat danach dieselben Startdaten.

Aktuell: der erste Admin (US15) und die Demoprodukte (US01). Ohne Admin könnte niemand die
Mitarbeiter-Maske benutzen, denn Mitarbeiter und Admins entstehen nur über diese Maske.
Ohne Demoprodukte wäre der Katalog in der Entwicklung leer.

Starten (im Repo-Ordner, mit aktiver .venv):
    python -m scripts.seed_db

Das Skript fragt nach E-Mail, Vor- und Nachname und Passwort des Admins. Bei E-Mail und
Namen reicht Enter für den Standardwert. Das Passwort steht bewusst
nicht im Code, damit kein Passwort im Repo landet.

Mehrfach starten ist ungefährlich: Gibt es die E-Mail schon, wird nichts angelegt.
"""

from getpass import getpass

from sqlalchemy import select

from app import config
from app.accounts import employee_service
from app.accounts.service import AccountError, get_user_by_email
from app.catalog import service as catalog_service
from app.catalog.models import Product
from app.catalog.service import PRODUCT_TYPE_CUSTOMER_IMAGE, PRODUCT_TYPE_FINISHED
from app.database import SessionLocal, init_db

DEFAULT_ADMIN_EMAIL = "admin@laserflow.local"
DEFAULT_ADMIN_FIRST_NAME = "Admin"
DEFAULT_ADMIN_LAST_NAME = "LaserFlow"

# Demoprodukte für den Katalog (US01). Namen, Texte, Maße und Preise stammen aus der
# früheren Liste in frontend/js/modules/products.js. Die Reihenfolge sorgt dafür, dass
# die drei Fertigprodukte in einer leeren Datenbank die IDs 1 bis 3 bekommen (Links
# wie produkt.html?id=2 funktionieren dann). Die Beschreibung ist ohne short_description
# getrennt, weil der erste Satz der Beschreibung die Kurzbeschreibung ist.
DEMO_PRODUCTS = [
    {
        "name": "X-Wing Starfighter",
        "short_description": "Detailreiches Raumschiff-Modell mit Standfuß und graviertem Namensschild.",
        "description": (
            "Über 20 lasergeschnittene Einzelteile, fein graviert und präzise ineinander gesteckt. "
            "Das Modell schwebt auf einem schmalen Stab über dem Standfuß, die Tragflächen stehen in "
            "der typischen X-Stellung. Vorne sitzt ein graviertes Namensschild. Ein Hingucker für "
            "Regal, Schreibtisch oder Vitrine."
        ),
        "width_mm": 115,
        "height_mm": 95,
        "depth_mm": 110,
        "price_cent": 2490,
        "product_type": PRODUCT_TYPE_FINISHED,
        "image_paths": [
            "img/produkte/x-wing-1.webp",
            "img/produkte/x-wing-2.webp",
            "img/produkte/x-wing-3.webp",
            "img/produkte/x-wing-4.webp",
        ],
    },
    {
        "name": "Britische Telefonzelle",
        "short_description": "Klassische Telefonzelle mit Sprossenfenstern und Gravur „TELEPHONE“.",
        "description": (
            "Die berühmte Telefonzelle als Holzmodell: vier Seiten mit ausgeschnittenen Sprossenfenstern, "
            "dahinter milchige Scheiben, oben die Krone und der Schriftzug „TELEPHONE“. "
            "Die Wände sind mit Fingerzinken verbunden. Oben offen, dadurch auch als Stifthalter "
            "oder mit einem LED-Teelicht als kleine Laterne nutzbar."
        ),
        "width_mm": 40,
        "height_mm": 100,
        "depth_mm": 40,
        "price_cent": 1490,
        "product_type": PRODUCT_TYPE_FINISHED,
        "image_paths": ["img/produkte/telefonzelle-1.webp", "img/produkte/telefonzelle-2.webp"],
    },
    {
        "name": "Mini-WC",
        "short_description": "Kleine Toilette aus geschichteten Holzlagen – mit Augenzwinkern.",
        "description": (
            "Aus vielen dünnen Holzschichten aufgebaut, dadurch entsteht die typische Streifenoptik. "
            "Mit Spülknopf auf dem Spülkasten und Gravur im Becken. "
            "Ein witziges Geschenk, ein Deko-Objekt für das Puppenhaus oder ein Halter für Büroklammern."
        ),
        "width_mm": 30,
        "height_mm": 38,
        "depth_mm": 45,
        "price_cent": 690,
        "product_type": PRODUCT_TYPE_FINISHED,
        "image_paths": ["img/produkte/mini-wc-1.webp", "img/produkte/mini-wc-2.webp", "img/produkte/mini-wc-3.webp"],
    },
    {
        # Platzhalter für US04 (Bild-Upload): der Kunde lädt hier sein eigenes Bild hoch.
        "name": "Gravurplatte (Demo)",
        "short_description": "Holzplatte für deine eigene Gravur.",
        "description": (
            "Du lädst ein Foto hoch, wir bereiten es auf und "
            "gravieren es auf die Platte. Platzhalter-Produkt für die Entwicklung, das echte Produkt "
            "legt das Team noch fest."
        ),
        "width_mm": 100,
        "height_mm": 80,
        "depth_mm": 4,
        "price_cent": 1290,
        "product_type": PRODUCT_TYPE_CUSTOMER_IMAGE,
        "engraving_width_mm": 80,
        "engraving_height_mm": 60,
        "image_paths": ["img/produkte/gravurplatte-platzhalter.svg"],
    },
]


def seed_first_admin(
    db,
    email: str,
    password: str,
    first_name: str = DEFAULT_ADMIN_FIRST_NAME,
    last_name: str = DEFAULT_ADMIN_LAST_NAME,
):
    """Legt den ersten Admin an, falls es die E-Mail noch nicht gibt.

    Args:
        db: Datenbank-Session.
        email: E-Mail des Admins.
        password: Passwort im Klartext (gespeichert wird nur der Hash).
        first_name, last_name: Name, wie er im Benutzermenü erscheint.

    Returns:
        der neue Admin oder None, wenn die E-Mail schon vergeben war.

    Raises:
        FieldValidationError: E-Mail, Passwort oder Name erfüllen die Regeln nicht.
    """
    if get_user_by_email(db, email) is not None:
        return None
    return employee_service.create_employee(db, email, password, first_name, last_name, "admin")


def seed_demo_products(db) -> int:
    """Legt die Demoprodukte an, die es noch nicht gibt (US01).

    Erkannt wird ein Produkt am Namen. Gibt es schon ein Produkt mit gleichem Namen,
    bleibt es unangetastet (auch wenn es inzwischen anders aussieht). So ist das Skript
    gefahrlos mehrfach startbar.

    Args:
        db: Datenbank-Session.

    Returns:
        Anzahl der neu angelegten Produkte (0, wenn alle schon da sind).

    Raises:
        InvalidProductTypeError: eine Produktart in DEMO_PRODUCTS ist unbekannt (Fehler im Code).
    """
    created = 0
    for demo in DEMO_PRODUCTS:
        exists = db.scalar(select(Product.id).where(Product.name == demo["name"]))
        if exists is not None:
            continue
        # Kurzbeschreibung als erster Satz vor die lange Beschreibung setzen (siehe short_description_of).
        description = demo["short_description"] + " " + demo["description"]
        catalog_service.create_product(
            db,
            name=demo["name"],
            description=description,
            width_mm=demo["width_mm"],
            height_mm=demo["height_mm"],
            depth_mm=demo.get("depth_mm"),
            price_cent=demo["price_cent"],
            product_type=demo["product_type"],
            engraving_width_mm=demo.get("engraving_width_mm"),
            engraving_height_mm=demo.get("engraving_height_mm"),
            image_paths=demo["image_paths"],
        )
        created += 1
    return created


def main() -> None:
    """Fragt die Admin-Daten ab, legt den Admin an und danach die Demoprodukte."""
    # Tabellen nur bei SQLite selbst anlegen. Bei Neon legt Alembic sie an (alembic upgrade head).
    if config.is_sqlite():
        init_db()
    email = input(f"E-Mail des ersten Admins [{DEFAULT_ADMIN_EMAIL}]: ").strip() or DEFAULT_ADMIN_EMAIL
    first_name = input(f"Vorname [{DEFAULT_ADMIN_FIRST_NAME}]: ").strip() or DEFAULT_ADMIN_FIRST_NAME
    last_name = input(f"Nachname [{DEFAULT_ADMIN_LAST_NAME}]: ").strip() or DEFAULT_ADMIN_LAST_NAME
    password = getpass("Passwort (mind. 8 Zeichen, Buchstabe und Ziffer; wird nicht angezeigt): ")

    db = SessionLocal()
    try:
        admin = seed_first_admin(db, email, password, first_name, last_name)
    except AccountError as error:
        # detail ist ein Text oder eine Liste mit Meldung pro Feld
        messages = [item["msg"] for item in error.detail] if isinstance(error.detail, list) else [error.detail]
        print("Nicht angelegt: " + " ".join(messages))
    else:
        if admin is None:
            print(
                f"Es gibt schon ein Konto mit {email}. Nichts geändert. "
                "Den Namen kannst du als Admin auf mitarbeiter.html ändern (Stift)."
            )
        else:
            print(
                f"Admin {first_name} {last_name} ({email}) angelegt. "
                "Anmelden unter http://127.0.0.1:8000/anmelden.html"
            )
    finally:
        db.close()

    # Eigene Session und immer ausführen, auch wenn der Admin nicht angelegt wurde.
    product_db = SessionLocal()
    try:
        created = seed_demo_products(product_db)
    finally:
        product_db.close()
    print(f"Demoprodukte: {created} neu angelegt.")


if __name__ == "__main__":
    main()
