"""Alembic-Umgebung für LaserFlow: steuert, wie Migrationen auf die Datenbank angewendet werden.

Was diese Datei tut:
- Die Datenbank-Adresse kommt aus app/config.py (also aus der .env), nicht aus alembic.ini.
- Target-Metadata ist Base.metadata. Daran vergleicht Alembic beim Erzeugen neuer
  Migrationen (--autogenerate), was sich in den Models geändert hat.
- Hat der Aufrufer eine Verbindung in config.attributes["connection"] hinterlegt, wird
  diese benutzt. So können Tests die Migration auf ihre eigene Datenbank anwenden.

Typische Befehle (im Repo-Ordner):
    alembic upgrade head                                  # Tabellen anlegen bzw. aktualisieren
    alembic revision --autogenerate -m "Beschreibung"     # neue Migration aus Model-Änderungen
    alembic downgrade base                                # alle Tabellen wieder entfernen
"""

from logging.config import fileConfig

from sqlalchemy import create_engine

from alembic import context
from app import config
from app.database import Base, engine_options, import_models

# Alle Models laden, damit Base.metadata alle Tabellen kennt.
import_models()

alembic_config = context.config

# Logging laut alembic.ini einrichten. disable_existing_loggers=False, damit das Einrichten
# die Logger der App (z. B. in Tests) nicht stillschweigend abschaltet.
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Erzeugt das SQL der Migrationen, ohne sich mit der Datenbank zu verbinden.

    Nützlich, um die SQL-Befehle vorab zu prüfen (`alembic upgrade head --sql`).
    Die Adresse kommt aus app/config.py.
    """
    context.configure(
        url=config.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=config.is_sqlite(),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Wendet die Migrationen direkt auf die Datenbank an.

    Ist in config.attributes["connection"] eine Verbindung hinterlegt (Tests), wird sie
    benutzt und NICHT geschlossen, denn sie gehört dem Aufrufer. Sonst öffnet diese
    Funktion eine eigene Verbindung zur Adresse aus app/config.py.

    Warum render_as_batch bei SQLite: SQLite kann Spalten nur eingeschränkt ändern.
    Alembic baut die Tabelle dann per "Batch" neu auf. Bei Postgres ist das nicht nötig.
    """
    shared_connection = alembic_config.attributes.get("connection")
    if shared_connection is not None:
        _run_with_connection(shared_connection)
        return

    engine = create_engine(config.DATABASE_URL, **engine_options(config.DATABASE_URL))
    with engine.connect() as connection:
        _run_with_connection(connection)
        connection.commit()
    engine.dispose()


def _run_with_connection(connection) -> None:
    """Führt die Migrationen über eine gegebene Verbindung aus.

    Args:
        connection: geöffnete SQLAlchemy-Verbindung, auf der die Migrationen laufen.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=config.is_sqlite(),
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
