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
2. `POST /api/auth/register` legt das Konto an.
3. E-Mail schon vergeben: Fehler direkt am Feld „E-Mail-Adresse“.
4. Erfolg: Das Formular wird durch den Hinweis ersetzt, die E-Mail zu bestätigen.

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

## Testen

- Module: im Ordner `frontend/` `npm test` (Node.js ab Version 20, keine Pakete nötig).
- Seiten: über Live Server öffnen. Ohne Backend erscheint nach dem Absenden „Der Server ist gerade nicht erreichbar“; die Prüfung der Eingaben funktioniert trotzdem.

## Bekannte Grenzen

- Das Backend (`/api/auth/...`) existiert noch nicht. Anmelden und Registrieren funktionieren erst, wenn die Router in `app/` gebaut sind.
- Nach dem Anmelden weiß das Benutzermenü noch nicht, dass jemand angemeldet ist (dafür braucht es eine Sitzungsabfrage im Backend, z. B. `GET /api/auth/me`).
- „Passwort vergessen“ ist in den Use Cases nicht vorgesehen und deshalb nicht umgesetzt.
- Die Links zu AGB und Datenschutz führen noch auf `#`.
