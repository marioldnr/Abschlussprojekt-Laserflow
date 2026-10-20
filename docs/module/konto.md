# Modul: Mein Konto

> Bereich: Kunde (Use Cases „Persönliche Daten verwalten“ und „Konto löschen“, `LaserFlow_Dokumentation.pdf`, Kapitel 1.5), User Story US10
> Stand: Frontend und Backend fertig (Daten ansehen und ändern, E-Mail und Passwort ändern, Profilbild, Konto löschen).
> Hinweis: Eine gemeinsame Vorlage `docs/module/_vorlage.md` gibt es noch nicht. Sobald sie existiert, wird diese Datei daran angepasst.

## Zweck

Angemeldete Kunden sehen auf „Mein Konto“ ihre Daten und können sie ändern: Name und Adresse, E-Mail-Adresse (mit Bestätigungscode), Passwort und Profilbild. Außerdem können sie ihr Konto löschen: Es wird sofort deaktiviert, die persönlichen Daten werden anonymisiert, sobald alle laufenden Bestellungen versendet sind. Bestell- und Rechnungsbelege bleiben erhalten.

**Akzeptanzkriterien US10 und wo sie umgesetzt sind**

| Kriterium | Umsetzung |
| --- | --- |
| Persönliche Daten in eigener Rubrik per Klick eingeben und ändern | Karte „Persönliche Daten“ mit Stift-Knopf (`konto.html`, `update_profile`) |
| Löschen erfordert Bestätigung im Bestätigungsfenster | `<dialog id="delete-dialog">` mit Passwort und Häkchen |
| Danach automatisch abgemeldet, Konto deaktiviert, keine erneute Anmeldung | `delete_account`: `is_active = False`, alle Sitzungen gelöscht, Cookie entfernt; `authenticate` lehnt deaktivierte Konten ab |
| Belege bleiben gespeichert, übrige Daten anonymisiert, sobald alle laufenden Bestellungen versendet sind | `anonymize_if_possible` / `_anonymize`; Bestellungen mit kopierter Adresse bleiben |
| Löschen auch bei laufenden Bestellungen, diese laufen normal weiter | Bestellungen werden nicht angefasst; anonymisiert wird erst, wenn keine mehr läuft |

## Dateien

**Frontend**

| Datei | Aufgabe |
| --- | --- |
| `frontend/konto.html` | Seite „Mein Konto“ nach Wireframe „Persönliche Daten verwalten“, mit Bestätigungsfenster zum Löschen |
| `frontend/css/konto.css` | Seitenaufbau: Profilbild, Karten, Löschen-Bereich |
| `frontend/js/konto.js` | Ablauf aller Bereiche der Seite |
| `frontend/js/modules/account-api.js` | Aufrufe unter `/api/account/...`, Prüfung der Bilddatei |
| `frontend/js/modules/api-client.js` | kann jetzt auch Dateien unverändert schicken (Option `file`) |
| `frontend/js/modules/auth-api.js` | `fieldErrorsFromApi()` kennt die Feldnamen dieser Seite |
| `frontend/js/layout.js` (Abschnitt 2) | Menü verlinkt „Mein Konto“ (den früheren Eintrag „Persönliche Daten“ gibt es nicht mehr, die Daten stehen auf „Mein Konto“), zeigt das Profilbild im Benutzer-Icon |
| `frontend/css/layout.css` | Stil `.user-avatar` für das Bild im Icon |
| `frontend/tests/account.test.js` | Tests von `account-api.js` |

**Backend** (Router → Service → Models)

| Datei | Aufgabe |
| --- | --- |
| `app/accounts/account_router.py` | Endpunkte `/api/account/...` |
| `app/accounts/account_service.py` | Logik: Daten ändern, E-Mail- und Passwortwechsel, Profilbild, Konto löschen und anonymisieren |
| `app/accounts/dependencies.py` | `get_current_user`: Login-Prüfung für Endpunkte (auch für andere Module) |
| `app/accounts/schemas.py` | Form der Anfragen und Antworten (`ProfileResponse`, `ProfileUpdate` …) |
| `app/accounts/validation.py` | `PROFILE_RULES`, `validate_fields()`; dieselben Regeln wie bei der Registrierung |
| `app/accounts/service.py` | `check_and_use_code()` und `create_and_send_code()`, gemeinsam mit der Registrierung |
| `app/accounts/models.py` | neue Spalten `users.avatar_path` und `users.pending_email` |
| `app/config.py` | `UPLOAD_DIR`, `AVATAR_MAX_BYTES` |
| `app/main.py` | ruft beim Start `anonymize_pending_accounts()` auf; liefert das Frontend mit `Cache-Control: no-cache` aus |
| `tests/test_account.py`, `tests/test_account_router.py` | Tests der Logik und der Endpunkte |

## Ablauf

1. Benutzermenü → „Mein Konto“. Wer nicht angemeldet ist, landet auf der Anmeldung und danach wieder hier.
2. **Profilbild:** „Bild ändern“ → Datei wählen. Der Browser prüft Format (JPG, PNG, WebP) und Größe (höchstens 5 MB), das Backend prüft noch einmal am Dateiinhalt. Das Bild erscheint sofort rund auf der Seite und oben im Benutzer-Icon. „Entfernen“ zeigt wieder das Standard-Symbol.
3. **Persönliche Daten:** Stift → Formular mit den aktuellen Daten → „Speichern“. Gleiche Regeln wie bei der Registrierung (z. B. Straße nur Buchstaben, Hausnummer „12a“). Fehler: Feld rot, Meldung darunter.
4. **E-Mail-Adresse:** Stift → neue Adresse + aktuelles Passwort → Code geht an die **neue** Adresse → Code eingeben. Erst dann gilt die neue Adresse; die alte bekommt einen Hinweis. Bis dahin meldet man sich mit der alten an. „Code erneut senden“ und „Abbrechen“ sind möglich.
5. **Passwort:** Stift → aktuelles Passwort, neues Passwort, Wiederholung. Danach sind alle anderen Geräte abgemeldet, dieses bleibt angemeldet.
6. **Konto löschen:** „Konto löschen …“ öffnet ein Bestätigungsfenster (erklärt, was passiert) → Passwort + Häkchen „Ich möchte mein Konto wirklich löschen“ → Konto deaktiviert, Kunde abgemeldet, nach 3 Sekunden Startseite.
7. **Anonymisieren (Backend):**
    - keine laufende Bestellung → sofort beim Löschen,
    - laufende Bestellungen (Status `ordered`, `paid`, `in_production`) → das Konto bleibt deaktiviert, bis alle versendet (`shipped`) oder storniert (`cancelled`) sind. Dann anonymisiert `anonymize_if_possible()`, aufgerufen beim Start der App und – **wichtig für die Story „Bestellstatus ändern“** – nach jedem Setzen auf `shipped`.

## Schnittstelle zum Backend (Vertrag)

Alle Endpunkte brauchen das Sitzungs-Cookie, sonst `401`.

| Methode und Pfad | Body | Antworten |
| --- | --- | --- |
| `GET /api/account` | – | `200` Kontodaten |
| `PUT /api/account/profile` | `{ first_name, last_name, street, house_number, postal_code, city }` | `200` Kontodaten · `422` Feldfehler |
| `PUT /api/account/password` | `{ current_password, new_password }` | `204` · `422` Feldfehler |
| `POST /api/account/email` | `{ new_email, password }` | `202 { pending_email }` · `422` Feldfehler |
| `POST /api/account/email/verify` | `{ code }` | `200` Kontodaten · `400` Code falsch · `409` keine offene Änderung oder Adresse inzwischen vergeben · `410` abgelaufen · `429` zu viele Versuche |
| `POST /api/account/email/resend-code` | – | `204` · `409` keine offene Änderung |
| `DELETE /api/account/email` | – | `204` (Änderung abgebrochen) |
| `GET /api/account/avatar` | – | `200` Bilddatei · `404` kein Bild |
| `PUT /api/account/avatar` | die Bilddatei selbst (kein Formular) | `200 { avatar_url }` · `422` Feld `avatar` |
| `DELETE /api/account/avatar` | – | `204` |
| `POST /api/account/delete` | `{ password }` | `204` (Cookie gelöscht) · `422` Passwort falsch |

Kontodaten: `{ email, pending_email, first_name, last_name, street, house_number, postal_code, city, created_at, avatar_url }`.
Auch `GET /api/auth/me` liefert jetzt `avatar_url` mit, damit das Icon auf jeder Seite das Bild zeigen kann.

## Bewusste Entscheidungen

- **Konto löschen in zwei Stufen** (Akzeptanzkriterien US10): sofort deaktivieren und abmelden, später anonymisieren. So können laufende Bestellungen mit Name und Adresse fertig bearbeitet und versendet werden (die Adresse steht zusätzlich kopiert in der Bestellung).
- **Was beim Anonymisieren bleibt:** die Zeile in `users` (damit Bestellungen ihr Konto behalten, Mitarbeiter sehen „Konto gelöscht“), alle Bestellungen mit Positionen und kopierter Liefer-/Rechnungsadresse (gesetzliche Aufbewahrungspflicht) und Kundenbilder, die zu einer Bestellung gehören.
- **Was entfernt wird:** Name, Anrede, E-Mail (wird `geloescht-<id>@anonymisiert.invalid`, die echte Adresse ist danach für eine neue Registrierung frei), Passwort-Hash, gespeicherte Adressen, Codes, Sitzungen, Profilbild, Warenkorb und Kundenbilder ohne Bestellung (Dateien und Zeilen).
- **Bestätigung mit Passwort** im Fenster, damit niemand am offenen Rechner fremde Konten löscht.
- **Neue E-Mail erst nach dem Code gültig** (`users.pending_email`): Sonst könnte man sich mit einem Tippfehler aussperren. Der Code nutzt dieselbe Prüfung wie die Registrierung (15 Minuten, 5 Versuche).
- **Passwort ändern beendet andere Sitzungen:** Falls jemand Fremdes angemeldet war, fliegt er raus.
- **Straße und Hausnummer** werden wie bei der Registrierung zusammen in `addresses.street` gespeichert und für das Formular mit `split_street()` wieder getrennt.
- **Profilbild ohne Bildbibliothek:** Das Bild wird unverändert gespeichert und erst bei der Anzeige rund und quadratisch zugeschnitten (CSS `object-fit: cover`). Das Format wird am Dateiinhalt erkannt („Magic Bytes“), nicht am Dateinamen.
- **Bild als Body statt Formular-Upload:** So braucht FastAPI kein Zusatzpaket (`python-multipart`).
- **Bilder im Dateisystem** unter `uploads/avatars/<user-id>-<zufall>.<endung>`, in der Datenbank nur der Pfad. Der Zufallsteil sorgt dafür, dass der Browser nach einem Wechsel das neue Bild lädt. Das alte Bild wird beim Ersetzen gelöscht.
- **Login-Prüfung als gemeinsamer Baustein:** `get_current_user` in `dependencies.py` können auch andere Module (Warenkorb, Bestellungen) benutzen.

## Testen

- Backend: im Repo-Ordner `pytest` (`test_account_router.py` braucht `httpx`).
- Frontend-Module: im Ordner `frontend/` `npm test`.
- Von Hand: `uvicorn app.main:app --reload`, anmelden, Benutzer-Icon → „Mein Konto“. Codes für die E-Mail-Änderung stehen im Terminal. Nach „Konto löschen“ (ohne Bestellungen) kann man sich mit derselben E-Mail neu registrieren.
- Nach dem Update einmal `laserflow.db` löschen (neue Spalten), danach neu registrieren.

## Bekannte Grenzen

- Solange noch Bestellungen laufen, ist die E-Mail-Adresse eines gelöschten Kontos belegt. Erst nach dem Anonymisieren kann man sich damit neu registrieren.
- Die Story „Bestellstatus ändern“ gibt es noch nicht. Bis sie `anonymize_if_possible()` nach dem Versand aufruft, wird nur beim Neustart der App nachgeholt.
- Ein gelöschtes Konto kann der Kunde nicht selbst wiederherstellen.
- Das Profilbild sieht nur der Kunde selbst; eine Ansicht für Mitarbeiter fehlt noch.
- Wer nach einem Update noch Fehler sieht, die schon behoben sind: einmal Strg + F5 (der Browser kann alte JavaScript-Dateien noch im Zwischenspeicher haben; seit `FrontendFiles` in `main.py` fragt er aber immer nach).
- Hochgeladene Dateien liegen im Repo-Ordner unter `uploads/`. Der Ordner darf nicht committet werden (lokal in `.git/info/exclude` eintragen, bis es eine gemeinsame `.gitignore` gibt).
- Für „Meine Bestellungen“ im Benutzermenü gibt es noch keine Seite.
