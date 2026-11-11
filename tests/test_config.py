"""Tests für die Datenbank-Adresse (app/config.py) und die Engine-Einstellungen (app/database.py).

Hier wird nie eine Verbindung aufgebaut. Die Tests prüfen nur Texte und Einstellungen,
damit sie auch ohne Netzwerk und ohne Neon-Zugang laufen.
"""

import pytest
from sqlalchemy import create_engine

from app import config
from app.database import engine_options

NEON_LIKE = "postgresql://benutzer:geheim@ep-test-123.example.invalid/laserflow?sslmode=require"


# Normalfall: Adressen werden richtig umgeschrieben

def test_none_gives_sqlite_default():
    """Ohne Angabe (keine .env) gilt die lokale SQLite-Datei."""
    assert config.normalize_database_url(None) == config.DEFAULT_DATABASE_URL
    assert config.DEFAULT_DATABASE_URL == "sqlite:///./laserflow.db"


def test_postgres_scheme_becomes_psycopg():
    """postgres:// wird zu postgresql+psycopg:// umgeschrieben."""
    url = "postgres://benutzer:geheim@host.example.invalid/db"
    assert config.normalize_database_url(url) == "postgresql+psycopg://benutzer:geheim@host.example.invalid/db"


def test_postgresql_scheme_becomes_psycopg():
    """postgresql:// (so liefert Neon die Adresse) wird zu postgresql+psycopg://."""
    assert config.normalize_database_url(NEON_LIKE).startswith("postgresql+psycopg://benutzer:geheim@")


def test_already_psycopg_stays_unchanged():
    """Eine Adresse mit schon richtigem Treiber bleibt unverändert."""
    url = "postgresql+psycopg://benutzer:geheim@host.example.invalid/db"
    assert config.normalize_database_url(url) == url


def test_sqlite_url_stays_unchanged():
    """SQLite-Adressen werden nicht angefasst."""
    assert config.normalize_database_url("sqlite:///./test.db") == "sqlite:///./test.db"


def test_query_parameters_are_kept():
    """Parameter nach dem Fragezeichen (z. B. sslmode von Neon) bleiben erhalten."""
    url = (
        "postgresql://benutzer:geheim@host.example.invalid/db"
        "?sslmode=require&channel_binding=require"
    )
    result = config.normalize_database_url(url)
    assert result.endswith("?sslmode=require&channel_binding=require")
    assert result == url.replace("postgresql://", "postgresql+psycopg://", 1)


# Normalfall: Leerzeichen und Anführungszeichen aus der .env

def test_surrounding_spaces_are_removed():
    """Leerzeichen vor und nach der Adresse werden entfernt."""
    assert config.normalize_database_url("  sqlite:///./x.db  ") == "sqlite:///./x.db"


def test_double_quotes_are_removed():
    """Doppelte Anführungszeichen (aus der .env-Vorlage) werden entfernt."""
    assert config.normalize_database_url(f'"{NEON_LIKE}"') == config.normalize_database_url(NEON_LIKE)


def test_single_quotes_are_removed():
    """Einfache Anführungszeichen werden ebenfalls entfernt."""
    assert config.normalize_database_url(f"'{NEON_LIKE}'") == config.normalize_database_url(NEON_LIKE)


def test_quotes_and_spaces_together():
    """Anführungszeichen mit Leerzeichen außen herum werden beide entfernt."""
    assert config.normalize_database_url(f'  "{NEON_LIKE}"  ') == config.normalize_database_url(NEON_LIKE)


# Ungültige oder leere Eingaben fallen auf den Standard zurück

@pytest.mark.parametrize("raw", ["", "   ", "\t", '""', "''", '" "'])
def test_empty_or_blank_gives_default(raw):
    """Leer, nur Leerzeichen oder leere Anführungszeichen ergeben den SQLite-Standard."""
    assert config.normalize_database_url(raw) == config.DEFAULT_DATABASE_URL


def test_single_quote_alone_is_not_stripped():
    """Ein einzelnes Anführungszeichen ist kein Paar und bleibt stehen."""
    assert config.normalize_database_url('"') == '"'


# is_sqlite

def test_is_sqlite_true_for_sqlite_urls():
    """SQLite-Adressen werden erkannt."""
    assert config.is_sqlite("sqlite:///./laserflow.db") is True
    assert config.is_sqlite("sqlite://") is True


def test_is_sqlite_false_for_postgres():
    """Postgres-Adressen sind keine SQLite-Adressen."""
    assert config.is_sqlite("postgresql+psycopg://u:p@h/db") is False


def test_is_sqlite_without_argument_uses_active_url():
    """Ohne Argument wird die aktive DATABASE_URL geprüft (in Tests: SQLite, siehe conftest)."""
    assert config.is_sqlite() is config.is_sqlite(config.DATABASE_URL)
    assert config.is_sqlite() is True


# Grenzfälle und Engine-Einstellungen

def test_engine_options_sqlite():
    """SQLite braucht check_same_thread=False, weil FastAPI in mehreren Threads arbeitet."""
    assert engine_options("sqlite:///./laserflow.db") == {"connect_args": {"check_same_thread": False}}


def test_engine_options_postgres():
    """Postgres bekommt pool_pre_ping, damit tote Verbindungen (Neon-Pause) erkannt werden."""
    assert engine_options("postgresql+psycopg://u:p@h/db") == {"pool_pre_ping": True}


def test_postgres_engine_uses_psycopg_v3():
    """Die umgeschriebene Adresse wählt den Treiber psycopg (Version 3).

    create_engine baut hier nur das Objekt, es wird keine Verbindung geöffnet.
    """
    url = config.normalize_database_url(NEON_LIKE)
    engine = create_engine(url, **engine_options(url))
    try:
        assert engine.dialect.driver == "psycopg"
    finally:
        engine.dispose()
