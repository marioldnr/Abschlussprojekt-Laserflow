"""Zentrale Einstellungen für LaserFlow.

Alles, was man je nach Rechner oder Umgebung anpassen möchte, steht hier an einer Stelle.
"""

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

# --- E-Mail-Versand (app/mail.py) ---

# "console": E-Mails werden nur im Terminal ausgegeben (zum Entwickeln, kein Mailserver nötig).
# "smtp":    E-Mails gehen an einen lokalen Mailserver (SMTP_HOST, SMTP_PORT).
MAIL_MODE = "console"
SMTP_HOST = "localhost"
SMTP_PORT = 1025
MAIL_SENDER = "LaserFlow <noreply@laserflow.local>"
