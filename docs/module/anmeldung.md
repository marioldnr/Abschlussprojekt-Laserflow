# Modul: Anmeldung und Registrierung

> Bereich: Besucher (Use Cases „Anmelden“ und „Registrieren“, `LaserFlow_Dokumentation.pdf`, Kapitel 1.2)
> Stand: Frontend fertig, Backend fehlt noch.
> Hinweis: Eine gemeinsame Vorlage `docs/module/_vorlage.md` gibt es noch nicht. Sobald sie existiert, wird diese Datei daran angepasst.

## Zweck

Besucher legen ein Kundenkonto an (Registrieren) und melden sich damit an (Anmelden). Erst angemeldete Kunden können Bilder hochladen und bestellen.

## Dateien

| Datei | Aufgabe |
| --- | --- |
| `frontend/anmelden.html` | Anmeldeseite nach Wireframe „Login“ |
| `frontend/registrieren.html` | Registrierungsseite nach Wireframe „Registrierung“ |
| `frontend/css/anmeldung.css` | Seitenaufbau beider Seiten (Glas-Karte, Icon, Wechsel-Link) |
| `frontend/js/anmelden.js` | Ablauf der Anmeldung |
| `frontend/js/registrieren.js` | Ablauf der Registrierung |
| `frontend/js/modules/validation.js` | Prüfregeln (E-Mail, Passwort, Name, Adresse …) |
| `frontend/js/modules/form.js` | Fehler anzeigen, Live-Prüfung, Passwort anzeigen |
| `frontend/js/modules/api-client.js` | Anfragen ans Backend, einheitliche Fehler |
| `frontend/js/modules/auth-api.js` | Aufrufe `/api/auth/login` und `/api/auth/register` |
| `frontend/js/modules/navigation.js` | sichere Weiterleitung nach dem Login |
| `frontend/agb.html` | AGB als eigene Seite; der Text steht nur hier (`#legal-text`) |
| `frontend/datenschutz.html` | Datenschutzerklärung als eigene Seite; der Text steht nur hier (`#legal-text`) |
| `frontend/css/rechtliches.css` | Aussehen der Seiten mit Rechtstexten |
| `frontend/js/modules/agb-dialog.js` | Popup für AGB und Datenschutz auf `registrieren.html`, lädt den Text aus der verlinkten Seite |
| `frontend/tests/*.test.js` | Tests der Module |

Die Formular-Styles (`.form`, `.field`, `.input`, `.alert` …) liegen in `frontend/css/components.css`, weil auch spätere Formulare (z. B. „Persönliche Daten verwalten“) sie brauchen.

## Ablauf

**Anmelden**

1. Klick auf „Anmelden“ im Benutzermenü öffnet `anmelden.html?weiter=<aktuelle Seite>`.
2. Pflichtfelder und E-Mail-Format werden im Browser geprüft.
3. `POST /api/auth/login` prüft die Zugangsdaten.
4. Fehler: Hinweis über dem Formular („E-Mail-Adresse oder Passwort ist falsch“ bzw. „Konto noch nicht bestätigt“), das Passwortfeld wird geleert.
5. Erfolg: Weiterleitung zum Ziel aus `?weiter=` (Use Case: „Zum gewählten Produkt zurückkehren“), sonst zur Startseite.

**Registrieren**

1. Eingaben werden im Browser geprüft: Pflichtfelder, E-Mail-Format, Name, Adresse auf Plausibilität (Straße mit Hausnummer, PLZ mit 5 Ziffern, Ort), Passwortstärke, Übereinstimmung der Passwörter, Zustimmung zu AGB und Datenschutz.
   - Die Links „AGB“ und „Datenschutzerklärung“ in der Checkbox öffnen ein Popup mit dem jeweiligen Text (siehe „AGB und Datenschutz (Popup)“ unten). Das Schließen hakt die Checkbox nicht an.
2. `POST /api/auth/register` legt das Konto an.
3. E-Mail schon vergeben: Fehler direkt am Feld „E-Mail-Adresse“.
4. Erfolg: Das Formular wird durch den Hinweis ersetzt, die E-Mail zu bestätigen.

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

Das Frontend erwartet diese Endpunkte. Wer das Backend baut (Router → Service → Model), hält sich daran oder passt `auth-api.js` im selben Pull Request an.

| Methode und Pfad | Body | Antworten |
| --- | --- | --- |
| `POST /api/auth/login` | `{ email, password }` | `200` Kundendaten + Sitzungs-Cookie · `401` falsche Zugangsdaten · `403` Konto nicht bestätigt |
| `POST /api/auth/register` | `{ email, password, first_name, last_name, street, postal_code, city }` | `201` angelegt, Bestätigungs-E-Mail verschickt · `409` E-Mail schon registriert · `422` ungültige Daten |

Fehlerantworten im FastAPI-Format `{ "detail": "..." }`. Das Backend muss alle Prüfungen aus `validation.js` selbst noch einmal machen, das Passwort gehasht speichern und die E-Mail-Eindeutigkeit über die Datenbank sicherstellen.

## Bewusste Entscheidungen

- **Name und Adresse bei der Registrierung:** Das Wireframe zeigt nur E-Mail und Passwort, der Use Case „Registrieren“ verlangt aber „Adresse auf Plausibilität prüfen“. Die Adresse wird außerdem für den Versand gebraucht.
- **Passwortregel:** mindestens 8 Zeichen, mindestens ein Buchstabe und eine Ziffer. Das ist eine Annahme, solange die Akzeptanzkriterien der Story nichts anderes festlegen. Die Mindestlänge steht in `PASSWORD_MIN_LENGTH`.
- **`?weiter=` nur mit relativen Pfaden:** schützt vor Weiterleitungen auf fremde Seiten (Open Redirect), siehe `safeReturnTarget()`.
- **Fehler verschwinden erst beim Tippen, nicht beim Verlassen des Feldes:** Sonst rutscht der Absende-Button beim Klick nach oben und der Klick geht ins Leere.
- **Keine Bestätigungscode-Seite:** Die Wireframes zeigen eine Code-Eingabe, der Use Case spricht von „Registrierung per Link bestätigen“. Umgesetzt ist der Hinweis auf den Link; die Bestätigungsseite gehört zur Story „Registrierung per Link bestätigen“.

- **AGB/Datenschutz als eigene Seiten plus Popup (Mischform):** Der Text steht nur einmal (in `agb.html` bzw. `datenschutz.html`) und ist auch direkt verlinkbar. Das Popup lädt ihn nach, damit das ausgefüllte Registrierungsformular erhalten bleibt.
- **`fetch` direkt in `agb-dialog.js`, nicht über `api-client.js`:** Geladen wird eine eigene HTML-Seite, keine Backend-Schnittstelle (`/api/...`).
- **`<dialog>` mit `showModal()`:** Abdunkeln, Esc und Fokus im Fenster liefert der Browser, dadurch wenig eigener Code.
- **Checkbox wird nicht automatisch angehakt:** Die Zustimmung muss eine aktive Handlung des Kunden sein.
- **AGB-/Datenschutz-Inhalt nur aus den Stories abgeleitet:** Noch nicht entschiedene Punkte stehen sichtbar als „[noch offen]“ im Text (Kontakt-E-Mail, Versandkosten, Lieferdauer, Widerrufsbelehrung, Google-Fonts-Hinweis).

## Testen

- Module: im Ordner `frontend/` `npm test` (Node.js ab Version 20, keine Pakete nötig).
- Seiten: über Live Server öffnen. Ohne Backend erscheint nach dem Absenden „Der Server ist gerade nicht erreichbar“; die Prüfung der Eingaben funktioniert trotzdem.
- AGB-/Datenschutz-Popup: automatische Tests in `frontend/tests/agb-dialog.test.js` (mit Ersatz-Elementen, weil Node keinen Browser hat). Zusätzlich von Hand im Browser:
  1. „AGB“ anklicken: Popup öffnet, Überschrift und Text stimmen.
  2. Schließen und erneut öffnen: Text ist sofort da.
  3. Danach „Datenschutzerklärung“: Überschrift und Text wechseln.
  4. ✕, „Gelesen und schließen“, Esc, Klick daneben: Popup schließt jeweils.
  5. Checkbox ist danach nicht angehakt.
  6. Schmales Fenster (Handy): Button über volle Breite, nur der Text scrollt.
  7. `agb.html` und `datenschutz.html` direkt aufrufen: Seiten im LaserFlow-Design.

## Bekannte Grenzen

- Das Backend (`/api/auth/...`) existiert noch nicht. Anmelden und Registrieren funktionieren erst, wenn die Router in `app/` gebaut sind.
- Nach dem Anmelden weiß das Benutzermenü noch nicht, dass jemand angemeldet ist (dafür braucht es eine Sitzungsabfrage im Backend, z. B. `GET /api/auth/me`).
- „Passwort vergessen“ ist in den Use Cases nicht vorgesehen und deshalb nicht umgesetzt.
- Die Footer-Links „AGB“ und „Datenschutz“ auf allen Seiten führen noch auf `#` (eigenes Issue, betrifft die gemeinsame `vorlage.html`).
- In AGB und Datenschutzerklärung sind einige Punkte noch „[noch offen]“ (siehe „Bewusste Entscheidungen“).
- Die Seiten laden Schriften von Google Fonts; die IP-Adresse geht dabei an Google. Das steht in der Datenschutzerklärung; ob die Schriften lokal eingebunden werden, entscheidet das Team.
