"""Tests für die Alembic-Migrationen (alembic/versions/).

Die Tests laufen auf einer frischen SQLite-Datei im temporären Ordner, nie auf Neon.
Die Migrationen sind so geschrieben, dass sie auch auf Postgres laufen. Gegen Postgres
selbst sind sie in diesem Test nicht geprüft.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.database import Base, import_models

REPO_DIR = Path(__file__).resolve().parent.parent
ALEMBIC_INI = REPO_DIR / "alembic.ini"


@pytest.fixture
def engine(tmp_path):
    """Liefert eine Engine auf eine frische, leere SQLite-Datei und räumt danach auf."""
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    yield engine
    engine.dispose()


def make_alembic_config(connection):
    """Baut die Alembic-Konfiguration und gibt ihr die Verbindung des Tests mit.

    Der Pfad zum Migrations-Ordner wird absolut gesetzt, damit der Test unabhängig
    vom aktuellen Arbeitsverzeichnis läuft.
    """
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(REPO_DIR / "alembic"))
    cfg.attributes["connection"] = connection
    return cfg


def model_table_names():
    """Die Tabellennamen aller Models (Base.metadata), ohne Alembics eigene Tabelle."""
    import_models()
    return set(Base.metadata.tables)


# Normalfall

def test_upgrade_head_creates_all_model_tables(engine):
    """Nach `alembic upgrade head` gibt es genau die Model-Tabellen plus alembic_version."""
    with engine.begin() as connection:
        command.upgrade(make_alembic_config(connection), "head")

    tables = set(inspect(engine).get_table_names())
    assert tables == model_table_names() | {"alembic_version"}


def test_models_and_migrations_are_in_sync(engine):
    """Die Migrationen beschreiben genau den Stand der Models.

    Wer ein Model ändert, muss eine neue Migration schreiben (siehe docs/module/datenbank.md).
    Sonst schlägt dieser Test fehl: Die Datenbank in der Migration und die Models laufen
    dann auseinander. Der Vergleich prüft Tabellen, Spalten, Indizes und Fremdschlüssel.
    """
    with engine.begin() as connection:
        command.upgrade(make_alembic_config(connection), "head")
        context = MigrationContext.configure(connection)
        differences = compare_metadata(context, Base.metadata)

    assert differences == [], f"Models und Migrationen passen nicht zusammen: {differences}"


# Umkehrung

def test_downgrade_base_removes_model_tables(engine):
    """`alembic downgrade base` entfernt alle Model-Tabellen wieder."""
    with engine.begin() as connection:
        cfg = make_alembic_config(connection)
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")

    remaining = set(inspect(engine).get_table_names())
    assert remaining & model_table_names() == set()
