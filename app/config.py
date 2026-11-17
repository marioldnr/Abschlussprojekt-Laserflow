"""Zentrale Einstellungen für LaserFlow.

Alles, was man je nach Rechner oder Umgebung anpassen möchte, steht hier an einer Stelle.
"""

import os

from dotenv import load_dotenv

# Liest die Datei .env aus dem Ordner, in dem die App gestartet wird (Repo-Ordner).
# Werte aus der .env landen in den Umgebungsvariablen. Ist eine Variable schon gesetzt
# (z. B. im Terminal), gewinnt der gesetzte Wert: load_dotenv überschreibt nichts.
load_dotenv()

# Notfall-Datenbank ohne .env: eine lokale SQLite-Datei. "./" heißt: im Ordner, aus dem
# die App gestartet wird (bei uns der Repo-Ordner). Die Datei laserflow.db wird beim
# ersten Start automatisch angelegt.
DEFAULT_DATABASE_URL = "sqlite:///./laserflow.db"


def normalize_database_url(raw: str | None) -> str:
    """Macht aus der Adresse aus der .env eine Adresse, die SQLAlchemy versteht.

    Args:
        raw: Der Rohwert aus DATABASE_URL, z. B. aus der .env. Darf None sein.

    Returns:
        Die bereinigte Adresse. Ist nichts (oder nur Leerzeichen) angegeben, kommt
        DEFAULT_DATABASE_URL zurück. Neon liefert Adressen mit "postgresql://"; daraus
        wird "postgresql+psycopg://", damit SQLAlchemy den Treiber psycopg (Version 3)
        nutzt. Ohne diese Umwandlung würde SQLAlchemy den alten Treiber psycopg2 suchen,
        der bei uns nicht installiert ist.
    """
    if raw is None:
        return DEFAULT_DATABASE_URL

    url = raw.strip()
    # Anführungszeichen, die beim Kopieren aus der .env mitkommen, entfernen.
    if len(url) >= 2 and url[0] == url[-1] and url[0] in ("'", '"'):
        url = url[1:-1].strip()

    if not url:
        return DEFAULT_DATABASE_URL

    for old_prefix in ("postgres://", "postgresql://"):
        if url.startswith(old_prefix):
            return "postgresql+psycopg://" + url[len(old_prefix):]
    return url


# Die aktive Datenbank-Adresse: aus der .env (DATABASE_URL) oder die SQLite-Notfall-Datei.
DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL"))


def is_sqlite(url: str | None = None) -> bool:
    """Prüft, ob die Datenbank eine lokale SQLite-Datei ist.

    Args:
        url: Die zu prüfende Adresse. Ohne Angabe wird die aktive DATABASE_URL geprüft.

    Returns:
        True, wenn die Adresse mit "sqlite" beginnt, sonst False.
    """
    if url is None:
        url = DATABASE_URL
    return url.startswith("sqlite")

# --- Registrierung und Anmeldung (Modul accounts) ---

# Wie lange ein Bestätigungscode gültig ist und wie oft man sich vertippen darf.
# Ohne Grenze könnte man alle 10.000 vierstelligen Codes einfach durchprobieren.
VERIFICATION_CODE_VALID_MINUTES = 15
VERIFICATION_CODE_MAX_ATTEMPTS = 5

# Sitzungs-Cookie nach dem Anmelden: Name und wie lange man angemeldet bleibt.
SESSION_COOKIE_NAME = "laserflow_session"
SESSION_VALID_DAYS = 7

# --- Hochgeladene Dateien ---

# Ordner für hochgeladene Dateien (Profilbilder unter uploads/avatars/). Liegt im Repo-Ordner,
# gehört aber NICHT in Git (CLAUDE.md, Abschnitt 5). Wird beim ersten Upload angelegt.
UPLOAD_DIR = "./uploads"

# Profilbild: größte erlaubte Dateigröße (5 MB).
AVATAR_MAX_BYTES = 5 * 1024 * 1024

# --- Bildspeicher (app/storage.py) ---

# Neon Object Storage ist ein Speicher für Dateien in der Cloud, angesprochen wie Amazon S3.
# Das Team teilt die Datenbank, aber nicht den Ordner uploads/. Liegen die Bilder im
# Object Storage, sieht sie jedes Teammitglied. Die Werte kommen aus der .env (Neon-Console:
# "Connect" -> Reiter "Storage" -> "Parameters only"). Die Namen AWS_* sind die, die Neon dort
# anzeigt. Ohne STORAGE_BUCKET legt die App die Dateien lokal unter UPLOAD_DIR ab.
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "").strip().strip('"').strip("'")
STORAGE_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL_S3", "").strip().strip('"').strip("'")
STORAGE_REGION = os.getenv("AWS_REGION", "").strip().strip('"').strip("'")
STORAGE_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "").strip().strip('"').strip("'")
STORAGE_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip().strip('"').strip("'")

# --- E-Mail-Versand (app/mail.py) ---

# Versand über das Gmail-Konto des Teams (Team-Entscheidung 10.11.2026).
# Adresse und App-Passwort stehen in der eigenen .env (Vorlage: .env.example), nie im Code.
# Ohne sie landen E-Mails nur im Terminal; so kann jedes Teammitglied auch ohne
# Zugangsdaten weiterarbeiten.


def _env(name: str, default: str = "") -> str:
    """Liest eine Umgebungsvariable ohne Leerzeichen und Anführungszeichen drumherum."""
    return os.getenv(name, default).strip().strip('"').strip("'")


def default_mail_mode(user: str, password: str) -> str:
    """Echter Versand nur, wenn Adresse UND App-Passwort da sind, sonst Ausgabe im Terminal."""
    return "smtp" if user and password else "console"


SMTP_HOST = _env("LASERFLOW_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(_env("LASERFLOW_SMTP_PORT", "587") or "587")  # 587 = verschlüsselt per STARTTLS
SMTP_USER = _env("LASERFLOW_SMTP_USER")
# Google zeigt das App-Passwort in 4er-Gruppen mit Leerzeichen an; die Leerzeichen gehören nicht dazu.
SMTP_PASSWORD = _env("LASERFLOW_SMTP_PASSWORD").replace(" ", "")
SMTP_TIMEOUT_SECONDS = 15

# Gmail verschickt nur im Namen des angemeldeten Kontos, deshalb ist der Absender dessen Adresse.
MAIL_SENDER = f"LaserFlow <{SMTP_USER}>" if SMTP_USER else "LaserFlow <noreply@laserflow.local>"

# "smtp":    E-Mails gehen wirklich raus (über SMTP_HOST mit SMTP_USER/SMTP_PASSWORD).
# "console": E-Mails werden nur im Terminal ausgegeben, in dem uvicorn läuft.
# Standard: "smtp", wenn Adresse und Passwort in der .env stehen, sonst "console".
# Mit LASERFLOW_MAIL_MODE=console in der .env lässt sich der echte Versand abschalten.
MAIL_MODE = _env("LASERFLOW_MAIL_MODE") or default_mail_mode(SMTP_USER, SMTP_PASSWORD)
