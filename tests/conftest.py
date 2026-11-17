"""Gemeinsame Test-Hilfen für alle Tests.

Die Fixture ``db`` gibt jedem Test eine eigene, leere Datenbank im Arbeitsspeicher.
So berühren Tests nie die echte laserflow.db und beeinflussen sich nicht gegenseitig.
"""

import os
import tempfile

# Muss VOR den app-Imports stehen: app.main verbindet sich beim Import mit der Datenbank.
# Tests dürfen nie die echte Neon-Datenbank aus der .env berühren. Deshalb wird die
# Adresse hart auf eine SQLite-Datei in einem temporären Ordner gesetzt (nicht setdefault:
# eine schon gesetzte Variable aus der Umgebung soll Tests nicht umlenken).
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
# Tests nutzen nie den Neon-Bildspeicher, auch wenn die eigene .env einen Bucket enthält
# (load_dotenv überschreibt schon gesetzte Variablen nicht).
os.environ["STORAGE_BUCKET"] = ""
# Tests verschicken nie echte E-Mails, auch wenn die eigene .env Gmail-Zugangsdaten enthält.
os.environ["LASERFLOW_MAIL_MODE"] = "console"

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import init_db  # noqa: E402


@pytest.fixture
def db():
    """Liefert eine Session auf eine frische Test-Datenbank mit allen Tabellen."""
    engine = create_engine("sqlite://")  # leere Datenbank im Arbeitsspeicher
    init_db(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
