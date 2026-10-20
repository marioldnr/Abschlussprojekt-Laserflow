"""Startpunkt von LaserFlow.

Starten (im Repo-Ordner, mit aktiver .venv):
    uvicorn app.main:app --reload
Danach im Browser: http://127.0.0.1:8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.accounts.router import router as accounts_router
from app.database import init_db

# Alle Tabellen anlegen, die es in laserflow.db noch nicht gibt (siehe database.init_db).
init_db()

app = FastAPI(title="LaserFlow")

# Router der Fachmodule (Endpunkte unter /api/...). Neue Router hier ergänzen,
# immer VOR app.mount("/") weiter unten.
app.include_router(accounts_router)  # /api/auth/... (Registrieren, Bestätigen, Anmelden)

# Frontend ausliefern (HTML, CSS, JS, Bilder). Muss als Letztes stehen,
# weil "/" sonst alle anderen Pfade überdecken würde.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
