# Modul: Mitarbeiter verwalten (US15)

> Bereich: Admin (Story US15, „Mitarbeiter verwalten“)
> Stand: Frontend und Backend fertig (Anlegen, Bearbeiten, Rolle zuweisen, Liste mit Rollen, endgültig deaktivieren).
> Hinweis: Eine gemeinsame Vorlage `docs/module/_vorlage.md` gibt es noch nicht. Diese Datei folgt dem Aufbau von `docs/module/anmeldung.md`.

## Zweck

Als Admin möchte ich Mitarbeiteraccounts anlegen und bearbeiten und ihnen eine Rolle zuweisen, damit nur berechtigte Personen Zugriff auf die Verwaltung haben.

Admins legen Mitarbeiter und weitere Admins über eine Maske an, ändern deren Daten und Rolle und sehen alle Mitarbeiter mit ihrer Rolle in einer Liste. Mitarbeiter entstehen nur hier, nicht über die öffentliche Registrierung. Kunden können nicht angelegt oder bearbeitet werden.

## Dateien

**Frontend**

| Datei | Aufgabe |
| --- | --- |
| `frontend/mitarbeiter.html` | Seite „Mitarbeiter verwalten“: Formular links, Liste rechts |
| `frontend/css/mitarbeiter.css` | Seitenaufbau, Liste, Kennzahlen, Filter (nur diese Seite) |
| `frontend/js/mitarbeiter.js` | Ablauf: Liste laden, anlegen, bearbeiten, deaktivieren, filtern |
| `frontend/js/layout.js` | Gemeinsame Datei: Menüpunkt „Mitarbeiter verwalten“ im Benutzermenü, nur für Admins (`user.role === "admin"`) |

Die Formular-Bausteine (Prüfregeln, Fehleranzeige, Anfragen ans Backend) kommen aus `frontend/js/modules/` (`validation.js`, `form.js`, `api-client.js`, `auth-api.js`) und sind mit dem Modul Anmeldung geteilt.

**Backend** (Router → Service → Models)

| Datei | Aufgabe |
| --- | --- |
| `app/accounts/employee_router.py` | Endpunkte `/api/admin/employees`. Nutzt `require_admin` aus `app/accounts/dependencies.py` |
| `app/accounts/dependencies.py` | Gemeinsamer Baustein für alle Module: Anmeldung (`get_current_user`) und Rollenprüfung (`require_roles`, `require_employee`, `require_admin`) |
| `app/accounts/employee_service.py` | Logik: anlegen, auflisten, holen, ändern, letzten Admin schützen, deaktivieren |
| `app/accounts/employee_schemas.py` | Form der Anfragen und Antworten (Pydantic) |
| `scripts/seed_db.py` | Legt den ersten Admin an (`seed_first_admin()`), damit die Maske überhaupt benutzbar ist |
| `app/main.py` | Bindet den Router ein (eine Zeile, vor dem Ausliefern des Frontends) |

**Tests**

| Datei | Aufgabe |
| --- | --- |
| `tests/test_employee_service.py` | Tests der Logik (Normalfall, ungültige Eingaben, Grenzfälle) |
| `tests/test_employee_router.py` | Tests über HTTP: Zugriff nur für Admins, Statuscodes. Braucht `httpx` |
| `tests/test_dependencies.py` | Tests der Rollenprüfung über HTTP: 401 ohne Anmeldung, 403 bei falscher Rolle, Admin mit allen Mitarbeiterrechten. Braucht `httpx` |

Die Fehlerklassen (`EmployeeNotFoundError`, `LastAdminError`, `EmployeeInactiveError`) stehen in `employee_service.py`. Der Router wandelt sie über ihren `status_code` in HTTP-Antworten um. Ungültige Eingaben melden Service und Router als `FieldValidationError` (422, Meldung pro Feld), dieselbe Klasse wie bei der Registrierung.

## Ablauf

**Ersten Admin anlegen (einmal pro lokaler Datenbank)**

1. Im Repo-Ordner mit aktiver `.venv`: `python -m scripts.seed_db`.
2. E-Mail (Vorschlag `admin@laserflow.local`), Vor- und Nachname eingeben. Leer lassen = Standardwert „Admin LaserFlow“. Den Namen kann der Admin später auf `mitarbeiter.html` über den Stift ändern. Danach das Passwort eingeben. Das Passwort steht bewusst nicht im Code.
3. Mehrfach starten ist ungefährlich: Gibt es die E-Mail schon, wird nichts geändert.
4. Jedes Teammitglied hat eine eigene `laserflow.db` und legt seinen ersten Admin selbst an, auch nach jedem Löschen der Datei.

**Anmelden und Maske öffnen**

1. Anmelden unter `http://127.0.0.1:8000/anmelden.html` (mit dem Admin-Konto).
2. `http://127.0.0.1:8000/mitarbeiter.html` öffnen. Die Seite lädt die Liste. Ist niemand angemeldet (401), erscheint ein Link zur Anmeldung. Ist man kein Admin (403), erscheint nur der Hinweis, die Maske bleibt verborgen.
3. Alternativ über das Benutzermenü (Icon oben rechts): Für Admins erscheint dort der Punkt „Mitarbeiter verwalten“, nach „Meine Bestellungen“. Mitarbeiter und Kunden sehen ihn nicht. Das ist nur Komfort, der Schutz liegt im Backend (403).

**Anlegen**

1. Formular ausfüllen (Vorname, Nachname, E-Mail, Startpasswort, Rolle). Die Felder werden im Browser geprüft.
2. `POST /api/admin/employees`. Erfolg: Meldung „… wurde angelegt.“, die Liste wird neu geladen.
3. Fehler erscheinen am Feld: E-Mail schon vergeben (409), ungültige Eingaben (422).

**Bearbeiten**

1. Stift-Symbol in der Liste klicken (nur bei aktiven Konten). Das Formular wird mit den Daten gefüllt und wechselt in den Bearbeiten-Modus.
2. Passwort leer lassen = bleibt unverändert.
3. Speichern: `PUT /api/admin/employees/<id>`.

**Endgültig deaktivieren**

1. Im Bearbeiten-Modus „Account deaktivieren“ klicken. Eine Rückfrage weist darauf hin, dass dies nicht rückgängig zu machen ist.
2. Der Account bleibt mit allen Daten erhalten, kann sich nicht mehr anmelden und wird ausgegraut in der Liste angezeigt (Filter „Deaktiviert“). Er hat keinen Stift mehr und lässt sich nicht bearbeiten oder reaktivieren.

## Schnittstelle zum Backend (Vertrag)

Alle Endpunkte verlangen einen angemeldeten Admin (Sitzungs-Cookie).

| Methode und Pfad | Body | Antworten |
| --- | --- | --- |
| `GET /api/admin/employees` | – | `200` Liste · `401` nicht angemeldet · `403` kein Admin |
| `POST /api/admin/employees` | `{ email, password, first_name, last_name, role }` | `201` angelegt · `401` · `403` · `409` E-Mail schon vergeben · `422` ungültige Felder |
| `GET /api/admin/employees/{id}` | – | `200` Mitarbeiter · `401` · `403` · `404` nicht gefunden oder Kunde |
| `PUT /api/admin/employees/{id}` | `{ email, first_name, last_name, role, is_active, password }` (`password` optional) | `200` geändert · `400` letzter aktiver Admin bzw. Konto schon deaktiviert · `401` · `403` · `404` · `409` E-Mail vergeben · `422` ungültige Felder |

Mitarbeiter: `{ id, email, first_name, last_name, role, is_active }`, nie der Passwort-Hash.
Rollen: `employee` (Mitarbeiter) und `admin`. Andere Werte gibt es hier nicht (`customer` wird abgelehnt).
Fehlerantworten im FastAPI-Format `{ "detail": ... }`. Bei `422` ist `detail` eine Liste `[{ "loc": ["body", "<feld>"], "msg": "..." }]`, wie bei der Registrierung.

## Rollen und Rechte

Jedes Konto hat genau eine Rolle (`users.role`). Die Prüfung liegt zentral in `app/accounts/dependencies.py`, nicht in den einzelnen Routern.

| Rolle | Wert | Was sie darf (Ist-Stand) |
| --- | --- | --- |
| Kunde | `customer` | Registrieren, Anmelden, „Mein Konto“ (`/api/account/...`). Keine Mitarbeiterfunktionen. |
| Mitarbeiter | `employee` | Alles, was mit `require_employee` geschützt ist. Bisher hängt daran noch kein Endpunkt. Mitarbeiterfunktionen (z. B. Produkte, Bestellungen) folgen mit ihren Modulen. |
| Admin | `admin` | Alles, was ein Mitarbeiter darf (`require_employee` nennt `admin` ausdrücklich). Zusätzlich Mitarbeiter verwalten (`/api/admin/employees`, `require_admin`). |

**Antworten der Prüfung**

- `401` mit `{"detail": "Bitte melde dich an."}`: niemand ist angemeldet (oder die Sitzung ist abgelaufen).
- `403` mit `{"detail": "..."}`: angemeldet, aber die Rolle ist nicht erlaubt. Die Meldung hängt von der Abhängigkeit ab: `MSG_EMPLOYEE_ONLY` („Diese Funktion ist nur für Mitarbeiter.“) bzw. `MSG_ADMIN_ONLY` („Diese Seite ist nur für Admins.“).

**Benutzung in einem neuen Router**

```python
from fastapi import APIRouter, Depends

from app.accounts.dependencies import require_employee
from app.accounts.models import User

router = APIRouter(prefix="/api/example", tags=["Beispiel (Mitarbeiter)"])


@router.get("")
def list_items(user: User = Depends(require_employee)):
    ...  # läuft nur für angemeldete Mitarbeiter und Admins
```

Für einen Admin-Endpunkt: `Depends(require_admin)`. Der Router wird wie üblich in `app/main.py` vor `app.mount("/", …)` eingebunden.

**Warum eine Fabrik `require_roles` an einer Stelle**

- Der Server prüft jede Anfrage (US03). Eine Regel, die nur im Browser versteckt wird, schützt nichts.
- Alle Rollenregeln laufen über eine Funktion. So baut niemand eine eigene Prüfung nach, die später abweicht.
- Der Admin wird in jeder Regel ausdrücklich mit aufgezählt. Ein Admin hat nicht automatisch alle Rechte, nur weil er „höher“ ist. Wer ihm ein neues Recht geben will, schreibt es hin.
- Ohne Rolle (`require_roles()`) bricht der Aufbau mit `ValueError` ab, damit ein vergessenes Argument beim Start auffällt und nicht erst bei einer Anfrage.

## Bewusste Entscheidungen

- **Eigene Dateien `employee_*` statt Erweiterung von `service.py`/`router.py`:** So ändern US15 und die Registrierung (US02/US03) dieselben Dateien nicht gleichzeitig.
- **Mitarbeiter sind sofort bestätigt (`is_verified` = True):** Der Admin legt sie an, es gibt keinen Bestätigungscode. Ohne das Flag lässt `authenticate()` sie nicht anmelden.
- **Deaktivieren ist endgültig (PO-Entscheidung 20.10.2026):** Kein Reaktivieren. Ein deaktiviertes Konto wird vom Service nicht mehr geändert (`EmployeeInactiveError`, 400). Die Zeile bleibt erhalten, damit spätere Bezüge (z. B. Bestellungen) nicht ins Leere zeigen. Löschen nur per Flag (`is_active`).
- **Es bleibt immer mindestens ein aktiver Admin:** Sonst könnte niemand mehr Mitarbeiter verwalten. Der Versuch, den letzten Admin herabzustufen oder zu deaktivieren, gibt `400`.
- **Die Seite liegt flach unter `frontend/` statt unter `admin/`:** `navigation.js` baut Links relativ (z. B. `anmelden.html`). In einem Unterordner würden sie nicht mehr stimmen.
- **Deaktivierte Mitarbeiter werden wie gelöschte Kunden anonymisiert (PO-Entscheidung 20.10.2026):** Beim Start der App läuft `anonymize_pending_accounts()` (`app/accounts/account_service.py`, aufgerufen aus `app/main.py`). Sie anonymisiert jedes deaktivierte Konto ohne laufende Bestellung: E-Mail wird zu `geloescht-<id>@anonymisiert.invalid`, Vor- und Nachname werden leer (`None`), der Passwort-Hash wird ungültig. Die Zeile in `users` bleibt erhalten. Das passt zu „Deaktivieren ist endgültig“.
- **Passwort beim Bearbeiten optional:** Leer = bleibt. So muss der Admin das Passwort nicht jedes Mal neu eingeben.
- **Zugriff nur über das Backend geprüft:** `require_admin` (in `app/accounts/dependencies.py`) antwortet Kunden und Mitarbeitern mit `403`, nicht angemeldeten Besuchern mit `401`. Das Verstecken der Maske im Browser ist nur Komfort.
- **Anlegen über das Backend mit der gleichen Prüfung wie bei der Registrierung:** Prüfregeln für E-Mail, Name und Passwort kommen aus `app/accounts/validation.py`.

## Testen

- Backend: `pytest tests/test_employee_service.py tests/test_employee_router.py tests/test_dependencies.py` (die Router-Tests brauchen `httpx`, sonst werden sie übersprungen). Der volle Lauf: `pytest`.
- Frontend: `npm test` im Ordner `frontend/` (Node.js ab Version 20). Dieses Modul hat keine eigenen Frontend-Tests. Die Prüfregeln (`validation.js`), der API-Client (`api-client.js`) und die Weiterleitung (`navigation.js`) haben Tests.
- Von Hand: `uvicorn app.main:app --reload` starten, mit dem Admin aus `scripts/seed_db.py` anmelden, `http://127.0.0.1:8000/mitarbeiter.html` öffnen. Dann prüfen: Mitarbeiter anlegen, in der Liste sehen, bearbeiten, deaktivieren (Stift und Bearbeiten-Modus verschwinden). Mit einem Mitarbeiter-Konto `mitarbeiter.html` aufrufen: Die Seite zeigt nur den Hinweis „Diese Seite ist nur für Admins.“.
- Nach Änderungen an den Tabellen `laserflow.db` löschen und `python -m scripts.seed_db` erneut ausführen.

## Bekannte Grenzen

- Die Seite prüft die Rolle erst über die API, nicht schon beim Laden der HTML-Datei. Die Daten schützt das Backend, die Seite selbst ist für jeden erreichbar.
- Kein Passwort-Reset per E-Mail für Mitarbeiter.
- Keine Protokollierung, wer wann was geändert hat.
