"""Zentrale Einstellungen für LaserFlow.

Alles, was man je nach Rechner oder Umgebung anpassen möchte, steht hier an einer Stelle.

Geheime Werte (z. B. das App-Passwort für den E-Mail-Versand) stehen NICHT hier, sondern in
einer lokalen Datei ".env" im Repo-Ordner. Sie gehört nie ins Repo (CLAUDE.md, Abschnitt 5).
Vorlage: ".env.example".
"""

import os
from pathlib import Path

# Repo-Ordner (eine Ebene über app/). Hier liegt die .env.
PROJECT_DIR = Path(__file__).resolve().parent.parent


def load_env_file(path: Path) -> None:
    """Liest Zeilen der Form NAME=wert aus einer .env-Datei in die Umgebungsvariablen.

    Bewusst ohne Zusatzpaket (python-dotenv), die paar Zeilen reichen:
        - leere Zeilen und Zeilen mit # am Anfang werden übersprungen,
        - Anführungszeichen um den Wert werden entfernt,
        - eine schon gesetzte Umgebungsvariable gewinnt (wird nicht überschrieben).
    Gibt es die Datei nicht, passiert nichts.

    Args:
        path: Pfad zur .env-Datei.
    """
    if not path.is_file():
        return
    # Windows-Editoren speichern manchmal mit unsichtbarem Startzeichen (BOM) oder als UTF-16.
    # "utf-8-sig" entfernt das BOM; sonst hieße die erste Variable falsch und würde nicht gefunden.
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-16")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


def default_mail_mode(user: str, password: str) -> str:
    """Echter Versand nur, wenn Adresse UND App-Passwort da sind, sonst Ausgabe im Terminal."""
    return "smtp" if user and password else "console"


load_env_file(PROJECT_DIR / ".env")

# Pfad zur SQLite-Datenbankdatei. "./" heißt: im Ordner, aus dem die App gestartet wird
# (bei uns der Repo-Ordner). Die Datei laserflow.db wird beim ersten Start automatisch angelegt.
DATABASE_URL = "sqlite:///./laserflow.db"

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

# --- E-Mail-Versand (app/mail.py) ---

# Versand über das Gmail-Konto des Teams (Team-Entscheidung 10.11.2026).
# Adresse und App-Passwort kommen aus der lokalen .env. Ohne sie landen E-Mails nur im Terminal,
# so kann jedes Teammitglied auch ohne Zugangsdaten weiterarbeiten.
SMTP_HOST = os.environ.get("LASERFLOW_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("LASERFLOW_SMTP_PORT", "587"))  # 587 = verschlüsselt per STARTTLS
SMTP_USER = os.environ.get("LASERFLOW_SMTP_USER", "").strip()
# Google zeigt das App-Passwort in 4er-Gruppen mit Leerzeichen an; die Leerzeichen gehören nicht dazu.
SMTP_PASSWORD = os.environ.get("LASERFLOW_SMTP_PASSWORD", "").replace(" ", "")
SMTP_TIMEOUT_SECONDS = 15

# Gmail verschickt nur im Namen des angemeldeten Kontos, deshalb ist der Absender dessen Adresse.
MAIL_SENDER = f"LaserFlow <{SMTP_USER}>" if SMTP_USER else "LaserFlow <noreply@laserflow.local>"

# "smtp":    E-Mails gehen wirklich raus (über SMTP_HOST mit SMTP_USER/SMTP_PASSWORD).
# "console": E-Mails werden nur im Terminal ausgegeben, in dem uvicorn läuft.
# Standard: "smtp", wenn Adresse und Passwort in der .env stehen, sonst "console".
# Mit LASERFLOW_MAIL_MODE=console in der .env lässt sich der echte Versand abschalten.
MAIL_MODE = os.environ.get("LASERFLOW_MAIL_MODE") or default_mail_mode(SMTP_USER, SMTP_PASSWORD)
