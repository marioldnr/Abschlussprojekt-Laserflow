# LaserFlow – Regeln für alle KI-Assistenten im Team

> Diese Datei liegt im Root des Repos. Claude liest sie bei jedem Teammitglied automatisch.
> Die Regeln gelten für jede KI, die in diesem Projekt arbeitet. Ändern nur per Pull Request mit Zustimmung des Teams.

Wir sind ein Team, das parallel am selben Repo arbeitet. Das oberste Ziel dieser Regeln:
**Niemand macht die Arbeit eines anderen kaputt oder unvollständig.**

## 0. Zuerst lesen: das Projekt-Brain

Lies vor jeder Aufgabe **`docs/PROJEKT-BRAIN.md`**. Dort steht, was LaserFlow ist, welche User Stories es gibt, welche technischen Vorgaben gelten und wie wir nach Scrumban vorgehen (Rollen, Board, Events, Definition of Done, aktueller Sprint).
Wenn etwas im Brain fehlt oder veraltet ist, sag es dem Teammitglied, statt es selbst zu ändern (das Brain ist eine gemeinsame Datei, siehe Abschnitt 2).

---

## 1. Nur die aktuelle Aufgabe bearbeiten

- Du arbeitest **ausschließlich an der Aufgabe (Issue/Task), die dir das Teammitglied gerade nennt**. Frag zu Beginn nach, wenn unklar ist, welche das ist.
- Du änderst **nur Dateien, die für diese Aufgabe nötig sind**. Bevor du eine Datei änderst, nennst du sie und sagst kurz, warum.
- Du änderst **keine Dateien „nebenbei“**: kein Aufräumen, kein Umformatieren, kein Umbenennen, keine „Verbesserungen“ an Code, der nicht zur Aufgabe gehört. Wenn dir etwas auffällt, **schlägst du es vor** (z. B. als neues Issue), statt es zu ändern.
- Du **löschst, verschiebst oder benennst keine Dateien um**, ohne ausdrückliche Zustimmung.
- Wenn die Aufgabe eine Datei braucht, die jemand anderes gerade bearbeitet (siehe Abschnitt 3), **hörst du auf und sagst Bescheid**, statt sie zu ändern.

## 2. Gemeinsame Dateien nur nach Absprache

Manche Dateien betreffen alle. Diese änderst du **nur, wenn das Teammitglied ausdrücklich bestätigt, dass es mit dem Team abgesprochen ist**:

- Datenbankschema und Migrationen
- Abhängigkeiten und Projekt-Setup (z. B. `package.json`, `requirements.txt`, Lockfiles)
- Konfiguration (z. B. `.env.example`, Docker, Build-, Linter-Einstellungen)
- Gemeinsame Bausteine, die mehrere Stories nutzen (z. B. Layout/Navigation, Login-/Rechteprüfung, Datenbank-Verbindung)
- `README.md`, `CLAUDE.md`, `docs/PROJEKT-BRAIN.md`, `.gitignore`, alles unter `.github/`

Änderungen daran gehören in einen **eigenen, kleinen Pull Request**, nicht versteckt in einem Feature.

## 3. Wer arbeitet woran?

- Jede Aufgabe ist ein Issue mit einer **zugewiesenen Person**. Wer zugewiesen ist, „besitzt“ die Arbeit daran.
- Bevor du anfängst: prüfe, ob es **offene Branches oder Pull Requests** gibt, die dieselben Dateien betreffen. Wenn ja, weise darauf hin und schlage vor, sich abzusprechen.
- Du arbeitest **nie im Branch einer anderen Person** und änderst keine fremden Pull Requests.

## 4. Git-Regeln

- **Nie direkt auf `main`** committen oder pushen. Jede Aufgabe hat einen eigenen Branch: `feature/US04-bild-upload`, `fix/…`, `docs/…`.
- **Vor dem Start** und **vor dem Pull Request** den neuesten Stand von `main` holen (`git pull origin main` bzw. `main` in den Branch mergen), damit Konflikte früh auffallen.
- **Kein Force-Push**, kein `git reset --hard` auf geteilten Branches, kein Umschreiben der History.
- **Merge-Konflikte nie automatisch auflösen**, indem eine Seite einfach überschrieben wird. Konflikt zeigen, erklären, und das Teammitglied entscheidet; bei fremdem Code mit der anderen Person absprechen.
- **Kleine Commits** mit klarer Nachricht, z. B. `US04: Dateityp-Prüfung für Upload ergänzt`. Nur Dateien committen, die zur Aufgabe gehören (`git add <datei>`, nicht blind `git add .`).
- Pull Request mit `Closes #<Nummer>`. **Mindestens eine andere Person reviewt.** Die KI mergt nie, approvt nie und schließt keine Issues.

## 5. Was die KI sonst nicht darf

- Stories, Acceptance Criteria oder Prioritäten ändern (das entscheidet der Product Owner)
- Karten auf dem Board verschieben oder Aufgaben in den Sprint holen
- Secrets (Passwörter, API-Keys, `.env`) ins Repo schreiben
- Externe Dienste einbauen, die die Stories ausschließen: KI-Modelle laufen auf dem eigenen Server, E-Mails ohne Cloud-Dienst, Bezahlung wird nur simuliert

## 6. Wir lernen, die KI erklärt

Wir wollen selbst programmieren und unseren Code in der Präsentation erklären können. Die KI erklärt zuerst den Lösungsweg und arbeitet in kleinen, nachvollziehbaren Schritten, statt ganze Features auf einmal zu schreiben.

## 7. Im Zweifel: fragen

Wenn eine Regel unklar ist, eine Aufgabe fremde oder gemeinsame Dateien berührt oder eine Story widersprüchlich ist: **anhalten und nachfragen**, nicht raten.
