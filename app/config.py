"""Zentrale Einstellungen für LaserFlow.

Alles, was man je nach Rechner oder Umgebung anpassen möchte, steht hier an einer Stelle.
"""

# Pfad zur SQLite-Datenbankdatei. "./" heißt: im Ordner, aus dem die App gestartet wird
# (bei uns der Repo-Ordner). Die Datei laserflow.db wird beim ersten Start automatisch angelegt.
DATABASE_URL = "sqlite:///./laserflow.db"
