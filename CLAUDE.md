# LaserFlow – Regeln für Claude im Team

> Diese Datei liegt im Root des Repos. Claude Code liest sie bei jedem Teammitglied automatisch zu Beginn jeder Sitzung.
> Ändern nur per Pull Request mit Zustimmung des Teams.

Wir sind ein 3er-Team, das parallel am selben Repo arbeitet, jeder mit Claude. Das oberste Ziel dieser Regeln:
**Niemand macht die Arbeit eines anderen kaputt oder unvollständig.**

---

## 0. Projekt-Infos

- **Anwendung:** Web-App für personalisierte Lasergravuren (Upload → KI-Bildaufbereitung → Warenkorb → laserfertige Produktionsdatei). Läuft für Entwicklung und Demos lokal.
- **Tech Stack (festgelegt, nicht ändern):** Python 3.11–3.13, FastAPI, SQLAlchemy, SQLite; Bilddateien und Produktionsdateien (PNG, JPEG, SVG, DXF) im Dateisystem, in der Datenbank nur der Pfad. Frontend: HTML, CSS, JavaScript ohne Framework. KI-Bildaufbereitung mit vortrainierten Modellen (rembg/u2net) lokal auf dem Server.
- **Architektur:** modularer Monolith mit Schichten. Router (Endpunkte) → Services (Logik) → Models (Datenbank). Logik gehört in Services, nicht in Router.
- **Stories:** Die 15 User Stories mit Akzeptanzkriterien liegen in `docs/user-stories.md`. Vor jeder Aufgabe die passende Story lesen; die Akzeptanzkriterien sind der Maßstab.
- **Starten:** `uvicorn app.main:app --reload`
- **Testen:** `pytest`
- **Sprache:** Kommentare, Commit-Nachrichten und Erklärungen auf Deutsch; Variablen-, Funktions- und Dateinamen auf Englisch.

## 1. Nur die aktuelle Aufgabe bearbeiten

- Du arbeitest **ausschließlich an der Aufgabe (Issue/Task), die dir das Teammitglied gerade nennt**. Frag zu Beginn nach, wenn unklar ist, welche das ist.
- Du nennst **zu Beginn die Dateien, die du ändern oder anlegen willst**, und begründest sie kurz. Brauchst du später weitere Dateien, fragst du erneut.
- Tests zur eigenen Aufgabe gehören dazu und dürfen angelegt werden.
- Du änderst **keine Dateien „nebenbei“**: kein Aufräumen, kein Umformatieren, kein Umbenennen, keine „Verbesserungen“ an Code, der nicht zur Aufgabe gehört. Wenn dir etwas auffällt, **schlägst du es vor** (z. B. als neues Issue), statt es zu ändern.
- Du **löschst, verschiebst oder benennst keine Dateien um**, ohne ausdrückliche Zustimmung.
- Wenn die Aufgabe eine Datei braucht, die jemand anderes gerade bearbeitet (siehe Abschnitt 3), **hörst du auf und sagst Bescheid**, statt sie zu ändern.

## 2. Gemeinsame Dateien nur nach Absprache

Manche Dateien betreffen alle. Diese änderst du **nur, wenn das Teammitglied ausdrücklich bestätigt, dass es mit dem Team abgesprochen ist**:

- Datenbankmodelle, Schema und Migrationen
- Abhängigkeiten und Projekt-Setup (z. B. `requirements.txt`, `pyproject.toml`)
- Konfiguration (z. B. `.env.example`, Einstellungen, Linter)
- Gemeinsame Bausteine, die mehrere Stories nutzen (z. B. Layout/Navigation, Login-/Rechteprüfung, Datenbank-Verbindung, E-Mail-Versand)
- `README.md`, `CLAUDE.md`, `.gitignore`, alles unter `.github/` und `docs/`

Änderungen daran gehören in einen **eigenen, kleinen Pull Request**, nicht versteckt in einem Feature.

## 3. Wer arbeitet woran?

- Jede Aufgabe ist ein Issue mit einer **zugewiesenen Person**. Wer zugewiesen ist, „besitzt“ die Arbeit daran.
- Bevor du anfängst: führe `git fetch` aus und prüfe mit `git branch -r`, ob es Branches gibt, die dieselben Dateien betreffen könnten. Offene Pull Requests kannst du nur sehen, wenn das GitHub-Tool (`gh`) eingerichtet ist; sonst frag das Teammitglied danach. Bei Überschneidungen: darauf hinweisen und vorschlagen, sich abzusprechen.
- Du arbeitest **nie im Branch einer anderen Person** und änderst keine fremden Pull Requests.

## 4. Git-Regeln

- **Nie direkt auf `main`** committen oder pushen. Jede Aufgabe hat einen eigenen Branch: `feature/US04-bild-upload`, `fix/…`, `docs/…` (US-Nummer = Nummer der User Story).
- **Vor dem Start** und **vor dem Pull Request** den neuesten Stand von `main` holen (`git pull origin main` bzw. `main` in den Branch mergen), damit Konflikte früh auffallen.
- **Kein Force-Push**, kein `git reset --hard` auf geteilten Branches, kein Umschreiben der History.
- **Merge-Konflikte nie automatisch auflösen**, indem eine Seite einfach überschrieben wird. Konflikt zeigen, erklären, und das Teammitglied entscheidet; bei fremdem Code mit der anderen Person absprechen.
- **Kleine Commits** mit klarer Nachricht, z. B. `US04: Dateityp-Prüfung für Upload ergänzt`. Nur Dateien committen, die zur Aufgabe gehören (`git add <datei>`, nicht blind `git add .`).
- Pull Request mit `Closes #<Nummer>`. **Mindestens eine andere Person reviewt.** Claude mergt nie, approvt nie und schließt keine Issues.

## 5. Nicht ins Repo

- Secrets (Passwörter, API-Keys, `.env`)
- Die SQLite-Datenbankdatei
- Hochgeladene Kundenbilder und erzeugte Produktionsdateien
- KI-Modelldateien (z. B. das u2net-Modell, ca. 176 MB; wird beim ersten Start heruntergeladen)
- Virtuelle Umgebungen und Caches (`.venv/`, `__pycache__/`)

Wenn eine dieser Dateien in `git status` auftaucht: nicht committen, sondern auf `.gitignore` hinweisen.

## 6. Was Claude sonst nicht darf

- Stories, Akzeptanzkriterien oder Prioritäten ändern (das entscheidet der Product Owner)
- Karten auf dem Board verschieben oder Aufgaben in den Sprint holen
- Den Tech Stack ändern oder neue Frameworks einführen
- Externe Dienste einbauen, die die Stories ausschließen: KI-Modelle laufen auf dem eigenen Server, E-Mails ohne Cloud-Dienst (lokaler Mailserver), Bezahlung wird nur simuliert

## 7. Fertig heißt (Definition of Done)

Eine Aufgabe ist erst fertig, wenn:

- alle Akzeptanzkriterien der Story erfüllt sind,
- Tests für Normalfall, ungültige Eingaben und Grenzfälle existieren,
- `pytest` vollständig grün ist (auch die Tests der anderen),
- der Pull Request von einer anderen Person reviewt wurde.

## 8. Wir lernen, Claude erklärt

Wir wollen selbst programmieren und unseren Code in der Präsentation erklären können. Claude erklärt zuerst den Lösungsweg und arbeitet in kleinen, nachvollziehbaren Schritten, statt ganze Features auf einmal zu schreiben.

## 9. Im Zweifel: fragen

Wenn eine Regel unklar ist, eine Aufgabe fremde oder gemeinsame Dateien berührt oder eine Story widersprüchlich ist: **anhalten und nachfragen**, nicht raten.
