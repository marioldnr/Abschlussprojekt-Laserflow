"""Gemeinsame Test-Hilfen für alle Tests.

Die Fixture ``db`` gibt jedem Test eine eigene, leere Datenbank im Arbeitsspeicher.
So berühren Tests nie die echte laserflow.db und beeinflussen sich nicht gegenseitig.

``no_real_mails`` gilt automatisch für jeden Test: Auch wer lokal eine .env mit dem
Gmail-Passwort hat, verschickt beim Testen nie echte E-Mails.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import config
from app.database import init_db


@pytest.fixture(autouse=True)
def no_real_mails(monkeypatch):
    """Stellt den E-Mail-Versand für jeden Test auf "console" (nur Terminal)."""
    monkeypatch.setattr(config, "MAIL_MODE", "console")


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
