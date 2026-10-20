"""Gemeinsame Test-Hilfen für alle Tests.

Die Fixture ``db`` gibt jedem Test eine eigene, leere Datenbank im Arbeitsspeicher.
So berühren Tests nie die echte laserflow.db und beeinflussen sich nicht gegenseitig.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import init_db


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
