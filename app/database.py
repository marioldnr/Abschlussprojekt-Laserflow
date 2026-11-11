"""Datenbankverbindung für LaserFlow: Engine, Session und Base.

Diese Datei kennt nur die Verbindung, keine Tabellen. Die Tabellen (Models) liegen
in den Fachmodulen, z. B. app/accounts/models.py, und erben von Base.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL, is_sqlite


def engine_options(url: str) -> dict:
    """Liefert die passenden Einstellungen für create_engine je nach Datenbank.

    Args:
        url: Datenbank-Adresse, z. B. "sqlite:///./laserflow.db" oder die Neon-Adresse.

    Returns:
        Für SQLite: check_same_thread=False (FastAPI bearbeitet Anfragen in mehreren
        Threads, SQLite erlaubt das sonst nicht). Für Postgres: pool_pre_ping=True.

    Warum pool_pre_ping: Neon (Free Plan) pausiert die Datenbank nach 5 Minuten ohne
    Anfragen. Verbindungen, die vorher offen waren, sind danach tot. Mit pool_pre_ping
    prüft SQLAlchemy jede Verbindung vor dem Gebrauch und baut sie bei Bedarf neu auf.
    """
    if is_sqlite(url):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


# 1. Engine: die eigentliche Verbindung zur Datenbank (SQLite-Datei oder Neon).
engine = create_engine(DATABASE_URL, **engine_options(DATABASE_URL))

# 2. Session-Fabrik: erzeugt für jede Anfrage eine eigene Session
# (ein "Gesprächsfenster" zur Datenbank zum Lesen und Speichern).
SessionLocal = sessionmaker(bind=engine, autoflush=False)


# 3. Base: gemeinsame Basisklasse. Jede Klasse, die davon erbt, wird zu einer Tabelle.
class Base(DeclarativeBase):
    """Basisklasse für alle Datenbank-Models."""


# 4. get_db: gibt einem Endpunkt eine Session und schließt sie danach wieder.
def get_db():
    """Öffnet eine Datenbank-Session für eine Anfrage.

    Wird in Routern per ``Depends(get_db)`` benutzt. Das ``finally`` sorgt dafür,
    dass die Session auch bei einem Fehler geschlossen wird.

    Yields:
        Session: offene Datenbank-Session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 5. import_models: sorgt dafür, dass Base alle Tabellen kennt.
def import_models() -> None:
    """Importiert die models.py aller Fachmodule, damit Base alle Tabellen kennt.

    Erst durch den Import "kennt" Base die Tabellen. Neues Fachmodul mit Tabellen =
    hier eine Zeile ergänzen. Ohne Zeile fehlt die Tabelle in create_all und in den
    Alembic-Migrationen (alembic/env.py ruft diese Funktion ebenfalls auf).

    Der Import steht innerhalb der Funktion, weil die Models ihrerseits Base aus dieser
    Datei importieren. Ein Import oben in der Datei würde einen gegenseitigen Import
    beim Laden auslösen.
    """
    from app.accounts import models as accounts_models  # noqa: F401
    from app.catalog import models as catalog_models  # noqa: F401
    from app.images import models as images_models  # noqa: F401
    from app.orders import models as orders_models  # noqa: F401
    from app.production import models as production_models  # noqa: F401


# 6. init_db: legt alle Tabellen an (nur für SQLite).
def init_db(bind=engine):
    """Legt alle Tabellen an, die es in der Datenbank noch nicht gibt.

    Gedacht für SQLite (lokal und Tests). Bei Postgres/Neon legt Alembic die Tabellen an
    (`alembic upgrade head`), siehe docs/module/datenbank.md. create_all würde dort
    Änderungen am Schema unbemerkt vorbeilassen.

    Bestehende Tabellen werden NICHT verändert. Wer eine Spalte ändert oder ergänzt,
    löscht lokal die Datei laserflow.db, beim nächsten Start entsteht sie neu.

    Args:
        bind: Engine, in der die Tabellen angelegt werden (Standard: die Engine der
            aktiven DATABASE_URL, in Tests eine eigene Test-Datenbank).
    """
    import_models()
    Base.metadata.create_all(bind=bind)
