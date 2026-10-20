# Modul: Anmeldung und Registrierung

> Bereich: Besucher (Use Cases „Registrieren“, „Registrierung bestätigen“ und „Anmelden“, `LaserFlow_Dokumentation.pdf`, Kapitel 1.2)
> Stand: Frontend und Backend fertig (Registrieren, E-Mail per Code bestätigen, Anmelden, Abmelden).
> Hinweis: Eine gemeinsame Vorlage `docs/module/_vorlage.md` gibt es noch nicht. Sobald sie existiert, wird diese Datei daran angepasst.

## Zweck

Besucher legen ein Kundenkonto an (Registrieren), bestätigen ihre E-Mail-Adresse mit einem 4-stelligen Code und sind danach angemeldet. Später melden sie sich mit E-Mail und Passwort an. Erst angemeldete Kunden können Bilder hochladen und bestellen.

## Dateien

**Frontend**

| Datei | Aufgabe |
| --- | --- |
| `frontend/anmelden.html` | Anmeldeseite nach Wireframe „Login“ |
| `frontend/registrieren.html` | Registrierungsseite nach Wireframe „Registrierung“ |
| `frontend/bestaetigen.html` | Code-Eingabe nach Wireframes „Verifizierungsvorgang“ und „Bestätigung der Verifizierung“ |
| `frontend/css/anmeldung.css` | Seitenaufbau aller drei Seiten (Glas-Karte, Icon, Code-Feld, Wechsel-Link) |
| `frontend/js/anmelden.js` | Ablauf der Anmeldung |
| `frontend/js/registrieren.js` | Ablauf der Registrierung |
| `frontend/js/bestaetigen.js` | Code prüfen, „Code erneut senden“, Weiterleitung nach Erfolg |
| `frontend/js/modules/validation.js` | Prüfregeln (E-Mail, Passwort, Name, Adresse, Code …) |
| `frontend/js/modules/form.js` | Fehler anzeigen, Live-Prüfung, Passwort anzeigen |
| `frontend/js/modules/api-client.js` | Anfragen ans Backend, einheitliche Fehler |
| `frontend/js/modules/auth-api.js` | Aufrufe unter `/api/auth/...`, Feldfehler des Backends übersetzen |
| `frontend/js/modules/navigation.js` | sichere Weiterleitung, Link zur Bestätigungsseite |
| `frontend/js/layout.js` (Abschnitt 2) | Benutzermenü fragt `GET /api/auth/me`, „Abmelden“ |
| `frontend/agb.html` | AGB als eigene Seite; der Text steht nur hier (`#legal-text`) |
| `frontend/datenschutz.html` | Datenschutzerklärung als eigene Seite; der Text steht nur hier (`#legal-text`) |
| `frontend/css/rechtliches.css` | Aussehen der Seiten mit Rechtstexten |
| `frontend/js/modules/agb-dialog.js` | Popup für AGB und Datenschutz auf `registrieren.html`, lädt den Text aus der verlinkten Seite |
| `frontend/tests/*.test.js` | Tests der Module |

**Backend** (Router → Service → Models)

| Datei | Aufgabe |
| --- | --- |
| `app/accounts/router.py` | Endpunkte `/api/auth/...`, setzt das Sitzungs-Cookie |
| `app/accounts/service.py` | Logik: Konto anlegen, Passwort hashen, Code erzeugen und prüfen, Anmelden, Sitzungen |
| `app/accounts/validation.py` | Prüfregeln wie im Frontend, mit denselben deutschen Meldungen |
| `app/accounts/schemas.py` | Form der Anfragen und Antworten (Pydantic) |
| `app/accounts/models.py` | Tabellen `users`, `verification_codes`, `addresses`, `sessions` |
| `app/mail.py` | E-Mail-Versand (gemeinsamer Baustein): Terminal oder lokaler Mailserver |
| `app/config.py` | Code-Gültigkeit, Fehlversuche, Cookie, Mail-Einstellungen |
| `tests/test_accounts_service.py` | Tests der Logik |
| `tests/test_accounts_router.py` | Tests über HTTP (ganzer Ablauf), braucht `httpx` |

Die Formular-Styles (`.form`, `.field`, `.input`, `.alert` …) liegen in `frontend/css/components.css`, weil auch spätere Formulare (z. B. „Persönliche Daten verwalten“) sie brauchen.

## Ablauf

**Registrieren**

1. Eingaben werden im Browser geprüft: Pflichtfelder, E-Mail-Format, Name, Adresse auf Plausibilität (Straße mit Hausnummer, PLZ mit 5 Ziffern, Ort), Passwortstärke, Übereinstimmung der Passwörter, Zustimmung zu AGB und Datenschutz. Fehler: Feld rot, Meldung darunter (z. B. „Das Passwort muss mindestens einen Buchstaben und eine Ziffer enthalten.“).
   - Die Links „AGB“ und „Datenschutzerklärung“ in der Checkbox öffnen ein Popup mit dem jeweiligen Text (siehe „AGB und Datenschutz (Popup)“ unten). Das Schließen hakt die Checkbox nicht an.
2. `POST /api/auth/register`: Das Backend prüft alles noch einmal (`validation.py`), schreibt die E-Mail klein, legt das Konto (noch nicht bestätigt) und die Adresse als Lieferadresse an, speichert das Passwort als scrypt-Hash und schickt einen 4-stelligen Code per E-Mail.
3. Fehler vom Backend erscheinen ebenfalls am Feld: E-Mail schon vergeben (409) bzw. Feldfehler (422).
4. Erfolg: Weiter zu `bestaetigen.html?email=...`.

**E-Mail bestätigen**

1. Der Kunde gibt den Code aus der E-Mail ein (Browser prüft: genau 4 Ziffern).
2. `POST /api/auth/verify`: Code richtig → Konto bestätigt, Sitzung angelegt, Cookie gesetzt.
3. Erfolg: „Verifizierung erfolgreich!“, nach 3 Sekunden automatische Weiterleitung zur Startseite (oder zum Ziel aus `?weiter=`), angemeldet.
4. Fehler am Code-Feld: falsch (mit Anzahl der restlichen Versuche), abgelaufen, zu viele Versuche.
5. „Code erneut senden“ (`POST /api/auth/resend-code`) schickt einen neuen Code. Nur der neueste Code gilt.

**Anmelden**

1. Klick auf „Anmelden“ im Benutzermenü öffnet `anmelden.html?weiter=<aktuelle Seite>`.
2. Pflichtfelder und E-Mail-Format werden im Browser geprüft.
3. `POST /api/auth/login` prüft die Zugangsdaten.
4. Falsche Daten: beide Felder rot, unter dem Passwort „E-Mail-Adresse oder Passwort ist falsch.“, das Passwortfeld wird geleert.
5. Konto noch nicht bestätigt (403): neuer Code wird verschickt, Weiterleitung zu `bestaetigen.html` mit Hinweis.
6. Erfolg: Weiterleitung zum Ziel aus `?weiter=` (Use Case: „Zum gewählten Produkt zurückkehren“), sonst zur Startseite.

**Angemeldet sein und Abmelden**

- `layout.js` fragt auf jeder Seite `GET /api/auth/me`. Antwortet das Backend mit Kundendaten, zeigt das Benutzermenü „Angemeldet als Vorname Nachname“.
- „Abmelden“ ruft `POST /api/auth/logout` auf (Sitzung gelöscht, Cookie entfernt) und führt zur Startseite.

**AGB und Datenschutz (Popup)** (Issue #38)

1. Die Links in der Checkbox zeigen auf `agb.html` bzw. `datenschutz.html` und haben das Merkmal `data-agb-open`.
2. Klick: `agb-dialog.js` verhindert das Öffnen des neuen Tabs, öffnet das `<dialog>` mit `showModal()` und zeigt kurz „Text wird geladen …“.
3. Die Seite aus dem `href` wird per `fetch` geladen. Übernommen werden nur der Bereich `#legal-text` und die Überschrift (`.section-head h2`).
4. Jede Seite wird pro Seitenaufruf nur einmal geladen (Zwischenspeicher); beim nächsten Öffnen ist der Text sofort da.
5. Fehler beim Laden: Hinweis mit Link „In neuem Tab öffnen“; beim nächsten Öffnen wird neu geladen.
6. Schließen per ✕, „Gelesen und schließen“, Esc oder Klick auf den abgedunkelten Hintergrund.
7. Ohne JavaScript öffnen die Links die Seite einfach in einem neuen Tab (`target="_blank"`).

Weiteren Rechtstext anbinden: Seite aus `agb.html` kopieren, Text in `<article id="legal-text">` schreiben, Link mit `href="<seite>.html" target="_blank" rel="noopener" data-agb-open` setzen. Am JavaScript ändert sich nichts.

## Schnittstelle zum Backend (Vertrag)

| Methode und Pfad | Body | Antworten |
| --- | --- | --- |
| `POST /api/auth/register` | `{ email, password, first_name, last_name, street, postal_code, city }` | `201` angelegt, Code verschickt · `409` E-Mail schon registriert · `422` ungültige Daten |
| `POST /api/auth/verify` | `{ email, code }` | `200` Kundendaten + Sitzungs-Cookie · `400` Code falsch · `409` schon bestätigt · `410` Code abgelaufen · `429` zu viele Fehlversuche |
| `POST /api/auth/resend-code` | `{ email }` | `204` immer (auch bei unbekannter E-Mail) |
| `POST /api/auth/login` | `{ email, password }` | `200` Kundendaten + Sitzungs-Cookie · `401` falsche Zugangsdaten · `403` Konto nicht bestätigt |
| `GET /api/auth/me` | – | `200` Kundendaten · `401` nicht angemeldet |
| `POST /api/auth/logout` | – | `204` |

Kundendaten: `{ id, email, first_name, last_name, role }` (nie der Passwort-Hash).
Fehlerantworten im FastAPI-Format `{ "detail": "..." }`, die Texte sind schon auf Deutsch. Bei `422` ist `detail` eine Liste `[{ "loc": ["body", "<feld>"], "msg": "..." }]`; `fieldErrorsFromApi()` in `auth-api.js` ordnet sie den Formularfeldern zu.

## Bewusste Entscheidungen

- **Bestätigung per 4-stelligem Code statt Link** (Teamentscheidung, passt zu den Wireframes): 15 Minuten gültig, höchstens 5 Fehlversuche, danach muss ein neuer Code angefordert werden. Ohne diese Grenze könnte man alle 10.000 Codes durchprobieren. Werte in `app/config.py`.
- **Nach dem Bestätigen direkt angemeldet:** Der Kunde hat gerade bewiesen, dass ihm die E-Mail-Adresse gehört, ein zusätzliches Anmelden wäre unnötig.
- **Sitzung über eine Tabelle `sessions`:** Das Cookie enthält nur einen langen Zufallswert, die Tabelle ordnet ihn dem Konto zu. Abmelden = Zeile löschen. Cookie mit `httponly` (für JavaScript unsichtbar) und `samesite=lax`, 7 Tage gültig.
- **Passwort-Hash mit `hashlib.scrypt`:** in Python eingebaut, kein Zusatzpaket nötig; eigenes Salz pro Passwort.
- **Gleiche Meldung bei falscher E-Mail und falschem Passwort**, „Code erneut senden“ antwortet immer mit 204, „Konto nicht bestätigt“ kommt erst nach dem richtigen Passwort: So kann niemand herausfinden, welche E-Mail-Adressen registriert sind.
- **E-Mail wird kleingeschrieben gespeichert**, damit `Anna@…` und `anna@…` nicht zwei Konten werden.
- **Prüfregeln doppelt (Browser und Backend):** Browser-Prüfungen kann man umgehen. Wer eine Regel ändert, ändert sie in `validation.js` und `validation.py`.
- **E-Mails im Terminal** (`MAIL_MODE = "console"`): Beim Entwickeln steht der Code im Terminal, in dem uvicorn läuft. Für einen lokalen Mailserver `MAIL_MODE = "smtp"` setzen. Laut Vorgaben kein Cloud-Dienst.
- **Name und Adresse bei der Registrierung:** Das Wireframe zeigt nur E-Mail und Passwort, der Use Case „Registrieren“ verlangt aber „Adresse auf Plausibilität prüfen“. Die Adresse wird als Lieferadresse (`type = "shipping"`) gespeichert.
- **Passwortregel:** mindestens 8 Zeichen, mindestens ein Buchstabe und eine Ziffer (Backend zusätzlich höchstens 128 Zeichen).
- **`?weiter=` nur mit relativen Pfaden:** schützt vor Weiterleitungen auf fremde Seiten (Open Redirect), siehe `safeReturnTarget()`.
- **Fehler verschwinden erst beim Tippen, nicht beim Verlassen des Feldes:** Sonst rutscht der Absende-Button beim Klick nach oben und der Klick geht ins Leere.

- **AGB/Datenschutz als eigene Seiten plus Popup (Mischform):** Der Text steht nur einmal (in `agb.html` bzw. `datenschutz.html`) und ist auch direkt verlinkbar. Das Popup lädt ihn nach, damit das ausgefüllte Registrierungsformular erhalten bleibt.
- **`fetch` direkt in `agb-dialog.js`, nicht über `api-client.js`:** Geladen wird eine eigene HTML-Seite, keine Backend-Schnittstelle (`/api/...`).
- **`<dialog>` mit `showModal()`:** Abdunkeln, Esc und Fokus im Fenster liefert der Browser, dadurch wenig eigener Code.
- **Checkbox wird nicht automatisch angehakt:** Die Zustimmung muss eine aktive Handlung des Kunden sein.
- **AGB-/Datenschutz-Inhalt nur aus den Stories abgeleitet:** Noch nicht entschiedene Punkte stehen sichtbar als „[noch offen]“ im Text (Kontakt-E-Mail, Versandkosten, Lieferdauer, Widerrufsbelehrung, Google-Fonts-Hinweis).

## Testen

- Backend: im Repo-Ordner `pytest`. Die Endpunkt-Tests (`test_accounts_router.py`) brauchen `httpx` (`pip install httpx`), sonst werden sie übersprungen.
- Frontend-Module: im Ordner `frontend/` `npm test` (Node.js ab Version 20, keine Pakete nötig).
- Von Hand: `uvicorn app.main:app --reload` starten, `http://127.0.0.1:8000/registrieren.html` öffnen, registrieren, den Code aus dem Terminal abschreiben. Über Live Server funktioniert nur die Prüfung im Browser („Der Server ist gerade nicht erreichbar“).
- Nach der Änderung an den Tabellen einmal `laserflow.db` löschen, sonst fehlen die neue Tabelle `sessions` und die Spalte `failed_attempts`.
- AGB-/Datenschutz-Popup: automatische Tests in `frontend/tests/agb-dialog.test.js` (mit Ersatz-Elementen, weil Node keinen Browser hat). Zusätzlich von Hand im Browser:
  1. „AGB“ anklicken: Popup öffnet, Überschrift und Text stimmen.
  2. Schließen und erneut öffnen: Text ist sofort da.
  3. Danach „Datenschutzerklärung“: Überschrift und Text wechseln.
  4. ✕, „Gelesen und schließen“, Esc, Klick daneben: Popup schließt jeweils.
  5. Checkbox ist danach nicht angehakt.
  6. Schmales Fenster (Handy): Button über volle Breite, nur der Text scrollt.
  7. `agb.html` und `datenschutz.html` direkt aufrufen: Seiten im LaserFlow-Design.

## Bekannte Grenzen

- Der lokale Mailserver ist noch nicht eingerichtet. Mit `MAIL_MODE = "smtp"` und ohne laufenden Server schlägt die Registrierung mit einem Serverfehler fehl (das Konto ist dann angelegt, der Code kann über „Code erneut senden“ neu angefordert werden).
- „Code erneut senden“ ist nicht begrenzt (man könnte viele E-Mails auslösen).
- Abgelaufene Sitzungen werden erst gelöscht, wenn jemand sie benutzt.
- Wer sich mit einer falschen E-Mail-Adresse registriert, kann sie nicht ändern, sondern muss sich neu registrieren; das falsche, unbestätigte Konto bleibt bestehen.
- „Passwort vergessen“ ist in den Use Cases nicht vorgesehen und deshalb nicht umgesetzt.
- Die Links „Mein Konto“, „Meine Bestellungen“, „Persönliche Daten“ im Benutzermenü und zu AGB/Datenschutz führen noch auf `#`.
- Der Warenkorb-Zähler im Kopfbereich weiß noch nichts von der Anmeldung.
- Die Footer-Links „AGB“ und „Datenschutz“ auf allen Seiten führen noch auf `#` (eigenes Issue, betrifft die gemeinsame `vorlage.html`).
- In AGB und Datenschutzerklärung sind einige Punkte noch „[noch offen]“ (siehe „Bewusste Entscheidungen“).
- Die Seiten laden Schriften von Google Fonts; die IP-Adresse geht dabei an Google. Das steht in der Datenschutzerklärung; ob die Schriften lokal eingebunden werden, entscheidet das Team.
