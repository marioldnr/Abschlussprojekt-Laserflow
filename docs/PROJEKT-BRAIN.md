# LaserFlow – Projekt-Brain

> Das Gedächtnis des Projekts. Jede KI liest diese Datei, bevor sie im Projekt arbeitet (siehe `CLAUDE.md`).
> Hier steht, **was** wir bauen und **wie** wir vorgehen. Die Regeln für die KI stehen in `CLAUDE.md`.
> Pflege: Änderungen per Pull Request. Neue Entscheidungen unten im Entscheidungslog eintragen.

---

## 1. Das Projekt in einem Satz

**LaserFlow** ist ein Webshop für personalisierte Lasergravur: Kunden wählen ein Produkt, laden ein Bild hoch, das automatisch geprüft und per KI für die Gravur aufbereitet wird, und nach der Bestellung entsteht automatisch eine laserfertige Produktionsdatei.

## 2. Rahmen

- **Art:** Abschlussprojekt, Fach Wirtschaftsinformatik / Projektmanagement (RDF)
- **Bewertet werden:** das Produkt (Increment), die Dokumentation und die Präsentation am Ende
- **Stakeholder:** die Lehrkräfte
- **Repo:** `marioldnr/Abschlussprojekt-Laserflow`
- **Board:** GitHub Project „Laserflow Scrumban“
- **Tech-Stack:** _noch offen_ (TODO, wird im Team entschieden und hier eingetragen)

## 3. Nutzerrollen im Produkt

| Rolle | Was sie kann |
|---|---|
| **Besucher** | Katalog ansehen, sich registrieren |
| **Kunde** | anmelden, Bild hochladen, bestellen, Bestellhistorie und eigene Daten verwalten |
| **Mitarbeiter** | Bestellungen ansehen und Status ändern, Kunden- und Produktverwaltung, Produktionsdateien abrufen |
| **Admin** | alles vom Mitarbeiter, dazu Mitarbeiteraccounts und Rollen verwalten |

## 4. Die User Stories (Product Backlog)

**Das Product Backlog ist nicht fertig.** Es wird laufend weiterentwickelt: Der PO kann jederzeit neue Stories ergänzen, ändern, teilen oder umpriorisieren, z. B. nach Feedback im Sprint Review.

- **Maßgeblich sind immer die GitHub-Issues mit dem Label `user-story`** und ihre Reihenfolge auf dem Board, nicht diese Tabelle. Prüfe dort den aktuellen Stand.
- Neue Stories bekommen die nächste Nummer (`US16`, `US17`, …), das Label `user-story`, Acceptance Criteria als Checkboxen und Abhängigkeiten, und landen in der Spalte `Backlog`.
- Neue Stories kommen **nicht in den laufenden Sprint**, außer das Team entscheidet das gemeinsam und das Sprint Goal ist nicht gefährdet. Normalerweise werden sie im nächsten Sprint Planning berücksichtigt.
- Die KI legt keine Stories selbst an und ändert keine; sie darf Formulierungen vorschlagen, der PO entscheidet.

Stand der Übersicht: 2026-10-06 (Start mit 15 Stories). Bei neuen Stories die Tabelle per PR ergänzen.

| # | Story | Rolle | Kurz | Hängt ab von |
|---|---|---|---|---|
| US01 | Produktkatalog ansehen | Besucher | Produkte mit Bild, Maßen, Preis; Suche/Filter; ohne Login sichtbar | – |
| US02 | Registrieren | Besucher | E-Mail + Passwort, Double-Opt-In mit 4-stelligem Code | – |
| US03 | Anmelden | Kunde, Mitarbeiter | Login, Rollenrechte serverseitig prüfen | US02 |
| US04 | Bild hochladen und prüfen | Kunde | JPEG/PNG bis 5 MB, Auflösung, Kontrast, Schärfe | US03 |
| US05 | Hintergrund entfernen | Kunde | KI stellt Motiv frei, Original bleibt umschaltbar, max. 10 s | US04 |
| US06 | Motiv aufbereiten | Kunde | zuschneiden, skalieren, ggf. KI-Upscaling (max. ×4), Graustufen + Dithering | US04, US05 |
| US07 | Warenkorb und Bestellabschluss | Kunde | Menge, Adresse, simulierte Zahlung, Rechnung per Mail | US01, US03, US06 |
| US08 | Produktionsdatei erzeugen | Mitarbeiter | Vorlage laden, Gravur einsetzen, Packing, SVG/DXF | US06, US07, US14 |
| US09 | Bestellhistorie ansehen | Kunde | Status als Leiste, Lieferdatum, nur eigene Bestellungen | US07 |
| US10 | Persönliche Daten verwalten | Kunde | Daten ändern, Konto löschen (anonymisieren) | US03 |
| US11 | Bestellübersicht ansehen | Mitarbeiter | chronologisch, nach Kunde gruppiert, Downloads | US07, US08 |
| US12 | Bestellstatus ändern | Mitarbeiter | 4 Status, automatische Mails bei „in Bearbeitung“/„versendet“ | US11 |
| US13 | Kundenliste ansehen | Mitarbeiter | Suche/Filter, gelöschte Konten anonymisiert | US03 |
| US14 | Produkte verwalten | Mitarbeiter | anlegen, bearbeiten, ausverkauft, ausblenden (nie löschen) | US03 |
| US15 | Mitarbeiteraccounts verwalten | Admin | Accounts anlegen, Rollen zuweisen | US03 |

**Offener Punkt:** US02 sagt in der Übersicht „Bestätigung per Link“, im Text „vierstelliger Code“. Der PO entscheidet; bis dahin gilt der Text (Code).

## 5. Feste technische Vorgaben (aus den Acceptance Criteria)

- KI-Modelle (Freistellen, Upscaling) laufen **auf dem eigenen Server**, Kundenbilder gehen an keinen externen Dienst.
- E-Mails **ohne externen Cloud-Dienst**, lokal über einen lokalen Mailserver.
- Bezahlung (PayPal/Bank) wird **nur simuliert**.
- Passwörter werden **nur gehasht** gespeichert.
- Berechtigungen werden **bei jeder Anfrage auf dem Server** geprüft.
- Produktionsdateien als **SVG oder DXF** im Dateisystem; die Datenbank speichert nur den Pfad.
- Produkte werden **nie gelöscht**, nur ausgeblendet. Gelöschte Kundenkonten werden **anonymisiert**, Belege bleiben.

## 6. Wie wir vorgehen: Scrumban

Scrumban = **Scrum** (Rollen, Events, Artefakte) + **Kanban** (Board, WIP-Limit). Grundlage ist der RDF-Leitfaden „Scrumban“.

### Rollen
- **Product Owner (PO):** verantwortet und priorisiert das Product Backlog, formuliert Stories, nimmt Ergebnisse ab, organisiert das Sprint Review. Entscheidet das **Was**, nicht das **Wie**.
- **Scrum Master (SM):** moderiert die Events, achtet auf die Regeln, räumt Hindernisse weg, wählt die Retro-Methode. Kein Projektleiter, sondern Coach.
- **Developers:** alle im Team, dauerhaft. Planen ihre Arbeit selbst und entscheiden, **wie** umgesetzt wird.
- **PO und SM wechseln jeden Sprint.** Jede Person hat also 1–2 Rollen gleichzeitig.

### Artefakte
- **Product Backlog:** alle Stories, geordnet nach Priorität (gehört dem PO). Lebendes Dokument, wächst und ändert sich laufend.
- **Sprint Backlog:** Sprint Goal + ausgewählte Stories + Tasks (gehört den Developers).
- **Increment:** alles, was fertig ist und die Definition of Done erfüllt; muss am Sprintende nutzbar sein.

### Events
| Event | Bei uns |
|---|---|
| **Sprint** | ca. 2–5 Wochen, Länge ergibt sich aus den Terminen für Review und Retro. Läuft, wird nicht verlängert oder verkürzt. |
| **Sprint Planning** | 30–60 Min., alle dabei, SM moderiert. Drei Fragen: **Warum?** (Sprint Goal) · **Was?** (PO schlägt vor, Developers wählen) · **Wie?** (Stories in Tasks zerlegen). Schätzen mit **Planning Poker**. |
| **Weekly** | statt Daily, einmal pro Woche: Was habe ich beigetragen? Was mache ich als Nächstes? Gibt es Hindernisse? |
| **Sprint Review** | ca. 15 Min. mit den Lehrkräften, Increment zeigen, Feedback holen. PO lädt ein. |
| **Retrospektive** | nach dem Review, SM wählt Methode, Ergebnis: konkrete Verbesserungen für den nächsten Sprint. Bleibt im Team. |

### Board
`Backlog` → `ToDo (Sprint)` → `In Progress` (**WIP-Limit 3**) → `To Approve / Feedback` → `Done (Increment)`

- Erst fertig machen, dann Neues anfangen.
- Keine neuen Aufgaben im laufenden Sprint, wenn sie das Sprint Goal gefährden. Neue Ideen kommen ins Backlog.
- Acceptance Criteria stehen als Checkboxen im Issue, Tasks im Abschnitt „Tasks“.

### Scrum-Werte
Commitment · Courage · Focus · Openness · Respect

### Häufige Fehler, die wir vermeiden
Kein Sprint Goal · DoD nicht eingehalten · Scope mitten im Sprint ändern · Retro überspringen · PO nicht erreichbar · SM als Chef.

## 7. Arbeitsablauf pro Story

1. Story aus `ToDo (Sprint)` nehmen, im Issue zuweisen, Karte auf `In Progress`.
2. Eigener Branch von `main`: `feature/US04-bild-upload` (bzw. `fix/…`, `docs/…`).
3. Kleine Commits, z. B. `US04: Dateityp-Prüfung ergänzt`.
4. Pull Request mit `Closes #<Nummer>`, erfüllte Kriterien abhaken. Karte auf `To Approve / Feedback`.
5. Review durch mindestens eine andere Person, Abnahme durch den PO, dann Merge und `Done (Increment)`.

## 8. Definition of Done (Entwurf, im Team zu bestätigen)

Eine Story ist fertig, wenn:
- alle Acceptance Criteria erfüllt und im PR abgehakt sind,
- mindestens eine weitere Person den Code reviewt hat,
- die Person, die ihn geschrieben hat, ihn erklären kann,
- die Funktion lokal getestet wurde,
- keine Secrets im Code stehen,
- Doku/README bei Bedarf aktualisiert ist,
- der PO abgenommen hat.

Konzepte und Dokumente: vollständig, von einer weiteren Person gegengelesen, vom PO abgenommen.

## 9. Aktueller Stand

| | |
|---|---|
| Sprint | 1 (Planung läuft) |
| Zeitraum | TODO bis TODO |
| Product Owner | TODO |
| Scrum Master | TODO |
| Sprint Goal | TODO |
| Stories im Sprint | TODO |
| Review / Retro | TODO |

Rollenplan für alle Sprints: TODO

## 10. Entscheidungslog

| Datum | Entscheidung | Warum |
|---|---|---|
| 2026-10-06 | Vorgehen Scrumban mit GitHub Issues + GitHub Project als Board | Vorgabe RDF, alles an einem Ort |
| 2026-10-06 | Product Backlog bleibt offen, neue Stories als Issues ab US16 | Scrum: Backlog wird fortlaufend angepasst |
| 2026-10-06 | Regeln für alle KIs in `CLAUDE.md`, Projektwissen in `docs/PROJEKT-BRAIN.md` | Jedes Teammitglied nutzt eigenen Claude-Account, alle sollen gleich arbeiten |
