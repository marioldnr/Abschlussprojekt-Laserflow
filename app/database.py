"""Datenbankverbindung für LaserFlow: Engine, Session und Base.

Diese Datei kennt nur die Verbindung, keine Tabellen. Die Tabellen (Models) liegen
in den Fachmodulen, z. B. app/accounts/models.py, und erben von Base.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

# 1. Engine: die eigentliche Verbindung zur Datenbankdatei.
# check_same_thread=False ist nur für SQLite nötig: FastAPI bearbeitet Anfragen in
# mehreren Threads, SQLite erlaubt das sonst nicht.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

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


# 5. init_db: legt alle Tabellen an.
def init_db(bind=engine):
    """Legt alle Tabellen an, die es in der Datenbank noch nicht gibt.

    Hier werden die models.py aller Fachmodule importiert. Erst durch den Import
    "kennt" Base die Tabellen. Neues Fachmodul mit Tabellen = hier eine Zeile ergänzen.

    Bestehende Tabellen werden NICHT verändert. Wer eine Spalte ändert oder ergänzt,
    löscht lokal die Datei laserflow.db, beim nächsten Start entsteht sie neu.

    Args:
        bind: Engine, in der die Tabellen angelegt werden (Standard: laserflow.db,
            in Tests eine eigene Test-Datenbank).
    """
    # Import innerhalb der Funktion, weil die Models ihrerseits Base aus dieser Datei
    # importieren (sonst gegenseitiger Import beim Laden).
    from app.accounts import models as accounts_models  # noqa: F401
    from app.catalog import models as catalog_models  # noqa: F401
    from app.images import models as images_models  # noqa: F401
    from app.orders import models as orders_models  # noqa: F401
    from app.production import models as production_models  # noqa: F401

    Base.metadata.create_all(bind=bind)
