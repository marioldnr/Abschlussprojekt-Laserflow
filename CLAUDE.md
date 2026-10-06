# LaserFlow – Regeln für Claude im Team

> Diese Datei liegt im Root des Repos. Claude Code liest sie bei jedem Teammitglied automatisch zu Beginn jeder Sitzung.
> Ändern nur per Pull Request mit Zustimmung des Teams.
> Die wichtigsten Git-Regeln (kein Push auf `main`, kein Force-Push, Review Pflicht) sind zusätzlich per Branch Protection in GitHub abgesichert. Diese Datei ersetzt das nicht, sondern sorgt dafür, dass Claude das Projekt versteht und sich im Alltag sauber verhält.

Wir sind ein 3er-Team, das parallel am selben Repo arbeitet, jeder mit Claude. Das oberste Ziel dieser Regeln:
**Niemand macht die Arbeit eines anderen kaputt oder unvollständig.**

---

## 0. Projekt-Infos

- **Anwendung:** Web-App für personalisierte Lasergravuren (Upload → KI-Bildaufbereitung → Warenkorb → laserfertige Produktionsdatei). Läuft für Entwicklung und Demos lokal.
- **Tech Stack (festgelegt, nicht ändern):** Python 3.11–3.13, FastAPI, SQLAlchemy, SQLite; Bilddateien und Produktionsdateien (PNG, JPEG, SVG, DXF) im Dateisystem, in der Datenbank nur der Pfad. Frontend: HTML, CSS, JavaScript ohne Framework. KI-Bildaufbereitung mit vortrainierten Modellen (rembg/u2net) lokal auf dem Server.
- **Architektur:** modularer Monolith mit Schichten. Router (Endpunkte) → Services (Logik) → Models (Datenbank). Logik gehört in Services, nicht in Router.
- **Stories:** Jede Aufgabe gehört zu einer der 15 User Stories (US01–US15). Die Akzeptanzkriterien der Story sind der Maßstab. Liegen sie dir nicht vor, frag das Teammitglied danach, statt sie zu erraten.
- **Tests:** laufen mit `pytest`.
- **Sprache:** Kommentare, Docstrings, Doku, Commit-Nachrichten und Erklärungen auf Deutsch; Variablen-, Funktions- und Dateinamen auf Englisch.

### Wie wir arbeiten: Scrumban (nach dem RDF-Leitfaden)

Scrumban = Scrum (Rollen, Events, Artefakte) + Kanban (Board, WIP-Limit). Daran orientierst du dich bei jeder Aufgabe.

- **Rollen:** Product Owner (PO) und Scrum Master (SM) wechseln jeden Sprint, alle sind dauerhaft Developers. Der **PO** pflegt und priorisiert das Product Backlog und entscheidet, **was** gebaut wird. Der **SM** moderiert die Events und räumt Hindernisse weg (Coach, kein Chef). Die **Developers** entscheiden, **wie** umgesetzt wird. Die Lehrkräfte sind die Stakeholder.
- **Artefakte:** Das **Product Backlog** (alle Stories, vom PO priorisiert) wird laufend erweitert und angepasst, neue Stories sind normal. Das **Sprint Backlog** besteht aus Sprint Goal, ausgewählten Stories und Tasks und gehört den Developers. Das **Increment** ist alles, was die Definition of Done erfüllt; es muss am Sprintende nutzbar sein.
- **Events:**
  - **Sprint:** **4 Wochen.** Sprint Review und Retro können sich um bis zu eine Woche nach hinten verschieben, je nachdem, wann die Lehrkräfte Zeit haben. Ein laufender Sprint wird nicht willkürlich verlängert oder verkürzt.
  - **Sprint Planning:** 30–60 Min., alle dabei, SM moderiert. Warum? (Sprint Goal), Was? (PO schlägt vor, Developers wählen), Wie? (Stories in Tasks zerlegen). Schätzen mit Planning Poker.
  - **Weekly** statt Daily, einmal pro Woche: Was habe ich beigetragen, was mache ich als Nächstes, gibt es Hindernisse?
  - **Sprint Review:** ca. 15 Min. mit den Lehrkräften, das Increment zeigen und Feedback holen. Der PO lädt ein.
  - **Retrospektive:** nach dem Review, der SM wählt die Methode, das Ergebnis sind konkrete Verbesserungen.
- **Board:** `Backlog` → `ToDo (Sprint)` → `In Progress` (**WIP-Limit 3**) → `To Approve / Feedback` → `Done (Increment)`.
- **User Stories:** „Als [Rolle] möchte ich [Funktion], damit [Nutzen]“. Sie beschreiben das Was und Warum, nicht das Wie. Gute Stories folgen INVEST (unabhängig, verhandelbar, wertvoll, schätzbar, klein, testbar). Akzeptanzkriterien sind messbar und prüfbar.
- **Werte:** Commitment, Courage, Focus, Openness, Respect.

Was das für dich heißt:
- Du arbeitest nur an Aufgaben aus dem **aktuellen Sprint**. Steht eine Aufgabe nicht im Sprint oder ist das WIP-Limit erreicht, weist du darauf hin, bevor du anfängst.
- **Erst fertig machen, dann Neues anfangen.**
- Neue Ideen oder Wünsche während des Sprints kommen als Issue ins Backlog, nicht in den laufenden Sprint, wenn sie das Sprint Goal gefährden.
- Typische Fehler sprichst du an: kein Sprint Goal, DoD nicht eingehalten, Scope mitten im Sprint geändert.

## 1. Nur die aktuelle Aufgabe bearbeiten

- Du arbeitest **ausschließlich an der Aufgabe (Issue/Task), die dir das Teammitglied gerade nennt**. Frag zu Beginn nach, wenn unklar ist, welche das ist.
- Du nennst **zu Beginn die Dateien, die du ändern oder anlegen willst**, und begründest sie kurz. Brauchst du später weitere Dateien, fragst du erneut.
- Tests und Dokumentation zur eigenen Aufgabe gehören dazu und dürfen angelegt bzw. geändert werden (Doku: siehe Abschnitt 8).
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

**Ausnahme:** Moduldokus unter `docs/module/` (siehe Abschnitt 8) dürfen im Feature-PR der eigenen Story geändert oder neu angelegt werden. Die Vorlage `docs/module/_vorlage.md` und `docs/einstieg.md` bleiben gemeinsame Dateien.

Änderungen an gemeinsamen Dateien gehören in einen **eigenen, kleinen Pull Request**, nicht versteckt in einem Feature.

## 3. Wer arbeitet woran?

- Jede Aufgabe ist ein Issue mit einer **zugewiesenen Person**. Wer zugewiesen ist, „besitzt“ die Arbeit daran.
- Wenn die Aufgabe Dateien berührt, die vermutlich auch andere brauchen (z. B. gemeinsame Bausteine aus Abschnitt 2), frag das Teammitglied, ob gerade jemand daran arbeitet. Bei Überschneidungen: darauf hinweisen und vorschlagen, sich abzusprechen.
- Du arbeitest **nie im Branch einer anderen Person** und änderst keine fremden Pull Requests.

## 4. Git-Regeln

- **Nie direkt auf `main`** committen oder pushen. Jede Aufgabe hat einen eigenen Branch: `feature/US04-bild-upload`, `fix/…`, `docs/…` (US-Nummer = Nummer der User Story).
- **Vor dem Start** und **vor dem Pull Request** den neuesten Stand von `main` holen (`git pull origin main` bzw. `main` in den Branch mergen), damit Konflikte früh auffallen.
- **Kein Force-Push**, kein `git reset --hard` auf geteilten Branches, kein Umschreiben der History.
- **Merge-Konflikte nie automatisch auflösen**, indem eine Seite einfach überschrieben wird. Konflikt zeigen, erklären, und das Teammitglied entscheidet; bei fremdem Code mit der anderen Person absprechen.
- **Kleine Commits** mit klarer Nachricht, z. B. `US04: Dateityp-Prüfung für Upload ergänzt`. Nur Dateien committen, die zur Aufgabe gehören (`git add <datei>`, nicht blind `git add .`).
- Pull Request mit `Closes #<Nummer>`. **Mindestens eine andere Person reviewt.** Claude approvt nie und schließt keine Issues.
- **Nichts hochladen ohne Go:** Claude committet, pusht, öffnet Pull Requests oder mergt **nur, wenn das Teammitglied ausdrücklich das Go dafür gibt**. Vorher zeigt Claude, was genau geändert oder hochgeladen wird, und wartet auf die Antwort. Ein Go gilt nur für den genannten Schritt, nicht für alle folgenden.

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
- Docstrings und die Moduldoku zur Story aktuell sind (siehe Abschnitt 8): Ein Entwickler ohne Vorwissen versteht damit, was das Modul tut und wie man es erweitert,
- der Pull Request von einer anderen Person reviewt wurde.

## 8. Dokumentation für neue Entwickler

Ziel: Ein Software Engineer, der LaserFlow nicht kennt, kann sich allein über `docs/` und den Code einarbeiten.

**Aufbau:**

- `docs/einstieg.md`: Setup, Start, Tests, Architekturüberblick, Links zu allen Moduldokus (gemeinsame Datei).
- `docs/module/<bereich>.md`: eine Datei pro fachlichem Bereich (z. B. `bild-upload.md`, `warenkorb.md`), immer nach der Vorlage `docs/module/_vorlage.md`.
- Docstrings im Code.

**Bei jeder Code-Änderung:**

- **Docstrings** (Deutsch) für jede neue oder geänderte Funktion in Services und Routern: was sie tut, Parameter, Rückgabe, mögliche Fehler. Bei nicht offensichtlichen Stellen auch das *Warum*.
- **Moduldoku** des betroffenen Bereichs aktualisieren. Gibt es für den Bereich noch keine, legst du sie nach der Vorlage an und nennst das zu Beginn (Abschnitt 1).
- In der Moduldoku änderst du nur die Teile, die deine Story betreffen. Abschnitte zu fremden Stories schreibst du nicht um, sondern weist auf Unstimmigkeiten hin.
- Die Doku beschreibt den **Ist-Stand**: nichts dokumentieren, was es (noch) nicht gibt; bekannte Grenzen ehrlich unter „Bekannte Grenzen“ nennen.
- Bewusste Entscheidungen kurz mit Begründung festhalten, damit niemand sie später versehentlich „repariert“.
- **Am Ende der Aufgabe** nennst du ausdrücklich, welche Doku-Abschnitte du geändert hast oder warum keine Änderung nötig war.

## 9. Wir lernen, Claude erklärt

Wir wollen selbst programmieren und unseren Code in der Präsentation erklären können. Claude erklärt zuerst den Lösungsweg und arbeitet in kleinen, nachvollziehbaren Schritten, statt ganze Features auf einmal zu schreiben.

## 10. Im Zweifel: fragen

Wenn eine Regel unklar ist, eine Aufgabe fremde oder gemeinsame Dateien berührt oder eine Story widersprüchlich ist: **anhalten und nachfragen**, nicht raten.
