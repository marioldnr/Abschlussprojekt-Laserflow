"""Startpunkt von LaserFlow.

Starten (im Repo-Ordner, mit aktiver .venv):
    uvicorn app.main:app --reload
Danach im Browser: http://127.0.0.1:8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.accounts.account_router import router as account_router
from app.accounts.account_service import anonymize_pending_accounts
from app.accounts.employee_router import router as employee_router
from app.accounts.router import router as accounts_router
from app.database import SessionLocal, init_db

# Alle Tabellen anlegen, die es in laserflow.db noch nicht gibt (siehe database.init_db).
init_db()

# Gelöschte Konten anonymisieren, deren Bestellungen inzwischen alle versendet sind (US10).
with SessionLocal() as startup_db:
    anonymize_pending_accounts(startup_db)

app = FastAPI(title="LaserFlow")

# Router der Fachmodule (Endpunkte unter /api/...). Neue Router hier ergänzen,
# immer VOR app.mount("/") weiter unten.
app.include_router(accounts_router)  # /api/auth/... (Registrieren, Bestätigen, Anmelden)
app.include_router(account_router)  # /api/account/... (Mein Konto, US10)
app.include_router(employee_router)  # /api/admin/employees/... (Mitarbeiter verwalten, US15)


class FrontendFiles(StaticFiles):
    """Liefert das Frontend aus und verbietet dem Browser, alte Dateien ungefragt zu benutzen.

    Warum: Ohne diesen Header behält der Browser JavaScript-Dateien eine Weile im Zwischenspeicher.
    Nach einer Änderung (z. B. an js/modules/api-client.js) lief dann noch der alte Code.
    "no-cache" heißt: Der Browser fragt jedes Mal kurz nach, ob sich die Datei geändert hat.
    Ist sie gleich, kommt nur "304 Not Modified" zurück, das kostet fast nichts.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


# Frontend ausliefern (HTML, CSS, JS, Bilder). Muss als Letztes stehen,
# weil "/" sonst alle anderen Pfade überdecken würde.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", FrontendFiles(directory=FRONTEND_DIR, html=True), name="frontend")
