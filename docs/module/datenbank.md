# Modul: Datenbank (Neon/Postgres, SQLite, Migrationen)

> Bereich: Grundlage für alle Module (keine einzelne Story)
> Stand: Adresse aus der `.env`, Postgres (Neon) über Alembic, SQLite als Notfallnetz und für Tests.
> Hinweis: Eine gemeinsame Vorlage `docs/module/_vorlage.md` gibt es noch nicht. Diese Datei folgt dem Aufbau von `docs/module/mitarbeiter.md`.

## Zweck

LaserFlow nutzt eine gemeinsame Datenbank bei Neon (Postgres), damit alle im Team dieselben Daten sehen. Die lokale SQLite-Datei `laserflow.db` dient als Notfallnetz (z. B. ohne Internet) und in den Tests.

Die App liest die Adresse aus der Datei `.env` (Variable `DATABASE_URL`). Ohne `.env` läuft sie mit SQLite.

## Dateien

| Datei | Aufgabe |
| --- | --- |
| `app/config.py` | Liest die `.env`, macht aus der Adresse eine für SQLAlchemy passende Adresse (`normalize_database_url`), prüft mit `is_sqlite()` den Typ |
| `app/database.py` | Engine, Session, `Base`. `engine_options()` wählt die Einstellungen je Datenbank. `import_models()` lädt alle Models. `init_db()` legt Tabellen per `create_all` an (nur SQLite) |
| `app/main.py` | Ruft `init_db()` nur bei SQLite auf |
| `scripts/seed_db.py` | Ruft `init_db()` nur bei SQLite auf (Postgres: Tabellen per Alembic) |
| `.env.example` | Vorlage für die `.env` (ohne echte Zugangsdaten, im Repo) |
| `.gitignore` | Schließt `.env`, `*.db`, `uploads/`, `storage/` und Caches aus |
| `requirements.txt` | Alle Python-Pakete mit Mindestversion |
| `alembic.ini` | Alembic-Konfiguration. Die Adresse steht hier bewusst nicht drin |
| `alembic/env.py` | Verbindet Alembic mit `app/config.py` und `Base.metadata` |
| `alembic/versions/d48f76725dcb_startstruktur_alle_tabellen.py` | Startmigration: legt alle 12 Tabellen an, `downgrade` entfernt sie |
| `tests/test_config.py` | Tests für die Adress-Umwandlung, `is_sqlite` und `engine_options` |
| `tests/test_migrations.py` | Tests für `upgrade head`, Abgleich Models gegen Migrationen, `downgrade base` |
| `tests/test_database.py` | Tests der Tabellen und Beziehungen (mit `create_all` auf SQLite) |
| `tests/conftest.py` | Setzt `DATABASE_URL` für Tests fest auf eine SQLite-Datei im temporären Ordner |

## Ablauf

**Einrichten für ein Teammitglied (Schritt für Schritt)**

1. Im Repo-Ordner mit aktiver `.venv` die Pakete installieren: `pip install -r requirements.txt`.
2. Die Datei `.env.example` nach `.env` kopieren. Unter Windows z. B. in der Eingabeaufforderung: `copy .env.example .env`.
3. In `.env` die Adresse aus der Neon-Console eintragen: „Connect“ öffnen, Reiter „Postgres database“ wählen, „Connection pooling“ ausschalten. Das Passwort gehört nur in die lokale `.env`.
4. Tabellen anlegen bzw. aktualisieren: `alembic upgrade head`. Das ist nur nötig, wenn neue Migrationen dazugekommen sind. Mehrfach ausführen schadet nie.
5. App starten: `uvicorn app.main:app --reload`.

**Tabellen ändern (nur nach Absprache im Team, siehe CLAUDE.md Abschnitt 2)**

1. Model im Fachmodul ändern (z. B. `app/catalog/models.py`).
2. Neue Migration erzeugen: `alembic revision --autogenerate -m "Kurze Beschreibung"`.
3. Die erzeugte Datei in `alembic/versions/` prüfen. Autogenerate erkennt nicht alles (z. B. Umbenennungen), also den Inhalt gegen die Änderung lesen.
4. Anwenden: `alembic upgrade head`.
5. Die Migration gehört in denselben Pull Request wie die Model-Änderung.
6. Bestehende Migrationsdateien nie nachträglich ändern. Änderungen kommen immer in eine neue Datei.

**Ohne `.env` (SQLite)**

1. Ohne `.env` (oder mit leerem `DATABASE_URL`) nutzt die App die Datei `laserflow.db` im Repo-Ordner.
2. Beim Start legt `init_db()` fehlende Tabellen per `create_all` an. Vorhandene Tabellen bleiben unverändert.
3. Nach einer Model-Änderung die lokale `laserflow.db` löschen. Beim nächsten Start entsteht sie neu. Diese Datei wird nicht über Alembic geändert.

**Tests**

Die Tests nutzen nie die echte Neon-Datenbank. `tests/conftest.py` setzt `DATABASE_URL` hart auf eine SQLite-Datei im temporären Ordner, bevor die App geladen wird.

## Bewusste Entscheidungen

- **Die Adresse steht nur in der `.env`:** Passwörter gehören nicht ins Repo. `alembic.ini` enthält bewusst keine Adresse, `alembic/env.py` liest sie aus `app/config.py`.
- **Umwandlung auf `postgresql+psycopg://`:** Neon liefert `postgresql://`. SQLAlchemy würde dafür den alten Treiber `psycopg2` suchen. Wir nutzen `psycopg` (Version 3). `normalize_database_url()` macht die Umwandlung.
- **`pool_pre_ping` bei Postgres:** Neon (Free Plan) pausiert nach 5 Minuten ohne Anfragen. Alte Verbindungen sind dann tot. Mit `pool_pre_ping` prüft SQLAlchemy jede Verbindung vor dem Gebrauch und baut sie bei Bedarf neu auf.
- **`check_same_thread=False` nur bei SQLite:** FastAPI bearbeitet Anfragen in mehreren Threads. SQLite erlaubt das nur mit dieser Einstellung. Postgres braucht sie nicht.
- **`create_all` nur bei SQLite:** Bei Postgres legt Alembic die Tabellen an. `create_all` würde Änderungen am Schema unbemerkt vorbeilassen, weil es bestehende Tabellen nicht ändert. So laufen Code und Datenbank nicht auseinander.
- **Tests erzwingen SQLite (`conftest.py`):** Tests dürfen die gemeinsame Datenbank nie verändern. Ein gesetzter Wert aus der Umgebung wird bewusst überschrieben.
- **`.env` wird nicht überschrieben, wenn eine Variable schon gesetzt ist:** `load_dotenv()` lässt Werte aus der Umgebung gewinnen. So kann man eine Adresse für einen einzelnen Lauf im Terminal setzen.
- **Startmigration mit generischen Typen:** Die Migration nutzt nur Typen wie `sa.String`, `sa.Integer`, `sa.DateTime`. Sie soll auf SQLite und Postgres laufen.

## Testen

- Nur das Modul: `pytest tests/test_config.py tests/test_migrations.py tests/test_database.py`.
- Der volle Lauf: `pytest`.
- `test_models_and_migrations_are_in_sync` schlägt fehl, wenn ein Model geändert wurde, aber keine neue Migration existiert. Dann `alembic revision --autogenerate` ausführen und die Datei prüfen.
- Die Migrationstests laufen auf SQLite. Ein Lauf gegen Neon ist nicht Teil der automatischen Tests.

## Bekannte Grenzen

- **Alle teilen dieselbe Datenbank:** Testdaten, die jemand anlegt, sehen alle anderen im Team.
- **Hochgeladene Bilder liegen weiter lokal** im Ordner `uploads/`. Andere Teammitglieder sehen sie nicht, auch wenn die Datenbank geteilt ist. Die Datenbank speichert nur den Pfad.
- **Neon-Pause:** Der Free Plan pausiert nach 5 Minuten ohne Anfragen. Die erste Anfrage danach dauert einige Sekunden.
- **Migration von Hand gegen Postgres geprüft, nicht automatisch:** Die Startmigration lief am 11.11.2026 auf einer lokalen Postgres-16-Datenbank fehlerfrei (alle 12 Tabellen, kein Unterschied zu den Models, Registrierung über die App funktioniert). Die automatischen Tests laufen nur auf SQLite.
- **CLAUDE.md ist noch nicht angepasst:** Der Abschnitt „Datenbank“ beschreibt noch den alten Stand (nur SQLite, keine Migrationen). Die Änderung gehört in einen eigenen Pull Request (CLAUDE.md Abschnitt 2).
- **Keine Rückwärts-Sicherung:** Ein `alembic downgrade` löscht Tabellen samt Daten. Vor Downgrades in der gemeinsamen Datenbank im Team absprechen.
