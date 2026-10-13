# LaserFlow – Designsystem

> Verbindliche Gestaltungsregeln für alle Seiten von LaserFlow.
> Gilt für Menschen **und** für Claude. Wer eine neue Seite baut oder eine bestehende ändert, hält sich an dieses Dokument.
> Gemeinsame Datei: Änderungen nur per Pull Request mit Zustimmung des Teams.

Referenz-Umsetzung: `Laserflow/app/static/index.html` (Startseite) und `Laserflow/app/static/vorlage.html` (leere Seite zum Kopieren).

---

## 1. Look in einem Satz

Dunkel, edel und ruhig, mit einem leuchtenden Cyan-Akzent wie ein Laserstrahl. Serifenschrift für Überschriften, schlichte serifenlose Schrift für Text, sanfte Bewegungen statt greller Effekte.

## 2. Dateien und wofür sie da sind

Alle Dateien liegen unter `Laserflow/app/static/`.

| Datei | Inhalt | Wer darf ändern |
| --- | --- | --- |
| `css/design.css` | Design-Tokens (Farben, Schriften, Radius, Bewegung), Grundstile, Buttons, Animationen | nur nach Absprache |
| `css/layout.css` | Seitengerüst, Kopfbereich, Navigation, Benutzermenü, Abschnitte, Fußbereich | nur nach Absprache |
| `css/components.css` | wiederverwendbare Bausteine: Feature-Karten, Produktkacheln, Schritte, Kontaktkarte | nur nach Absprache |
| `js/layout.js` | Kopfbereich beim Scrollen, Benutzermenü, Einblenden beim Scrollen | nur nach Absprache |
| `css/<seite>.css`, `js/<seite>.js` | alles, was es nur auf **einer** Seite gibt (z. B. `startseite.css`) | wer die Seite baut |
| `vorlage.html` | leere Seite mit Kopf- und Fußbereich zum Kopieren | nur nach Absprache |

Reihenfolge im `<head>` jeder Seite (aus `vorlage.html` übernehmen, nicht umsortieren):

1. Favicons und Google Fonts (Cormorant Garamond, Inter)
2. `design.css` → `layout.css` → `components.css`
3. `js/layout.js` (mit `defer`)
4. danach die seiteneigenen Dateien

## 3. Neue Seite anlegen

1. `vorlage.html` kopieren und sinnvoll benennen, z. B. `warenkorb.html`.
2. `SEITENTITEL` im `<title>` ersetzen.
3. Inhalte **nur innerhalb von `<main>`** schreiben. Kopfbereich und Fußbereich bleiben unverändert.
4. Erst vorhandene Bausteine aus `components.css` verwenden (siehe Abschnitt 6).
5. Braucht die Seite eigene Styles, eine Datei `css/<seite>.css` anlegen und in der Vorlage einkommentieren. Gleiches gilt für JavaScript.
6. Links zu Abschnitten der Startseite immer mit Dateinamen schreiben: `index.html#kontakt`, nicht nur `#kontakt`.

## 4. Farben

Farben **nie** als Hex-Wert in Seiten-CSS schreiben, immer die Variable benutzen.

| Variable | Wert | Einsatz |
| --- | --- | --- |
| `--bg` | `#161412` | Seitenhintergrund |
| `--bg-alt` | `#1f1c19` | abwechselnde Abschnitte (`.section-alt`) |
| `--surface` | `#26221e` | Karten, Menüs, Badges |
| `--text` | `#f3ede6` | Haupttext |
| `--muted` | `#b3a89c` | Nebentext, Beschreibungen |
| `--accent` | `#97ffff` | Akzent (DarkSlateGray1): Buttons, Links beim Darüberfahren, Linien, Icons |
| `--accent-2` | `#d2ffff` | hellere Variante, nur für Verläufe |
| `--on-accent` | `#10201f` | Schrift **auf** Akzentflächen (z. B. Button-Text) |
| `--border` | `#3a342e` | Rahmen und Trennlinien |
| `--glow` | `rgba(151,255,255,0.3)` | Leuchten und farbige Schatten |

Regeln:

- Akzentfarbe sparsam einsetzen: pro Bildschirmhöhe höchstens ein gefüllter Akzent-Button.
- Text auf Akzentflächen immer `--on-accent`, sonst ist er nicht lesbar.
- Fehler- oder Erfolgsfarben gibt es noch nicht. Wer sie braucht (z. B. für Formulare), schlägt sie als neue Tokens in `design.css` vor, statt eigene Farben zu erfinden.

## 5. Schrift, Abstände, Formen

- **Überschriften** (`h1`–`h3`): `--font-head` (Cormorant Garamond), Gewicht `--head-weight`.
- **Fließtext**: `--font-body` (Inter).
- **Kleine Überzeile** über Überschriften: `<p class="eyebrow">Bereich</p>`, Großbuchstaben, Akzentfarbe.
- **Ecken**: immer `var(--radius)` (10 px). Große Karten dürfen `calc(var(--radius) * 1.5)` nehmen.
- **Seitenbreite**: Inhalte immer in `<div class="container">` (max. 1160 px, 20 px Rand).
- **Abschnitte**: `<section class="section">` (90 px Abstand oben/unten). Für Abwechslung `class="section section-alt"`.

## 6. Bausteine (Klassen zum Wiederverwenden)

| Baustein | Klassen | Datei |
| --- | --- | --- |
| Button (gefüllt) | `.button` | design.css |
| Button (Umriss) | `.button .button-ghost` | design.css |
| Buttons nebeneinander | `.button-row` | design.css |
| Überzeile | `.eyebrow` | design.css |
| Abschnittskopf | `.section-head` mit `.eyebrow`, `h2`, `.section-intro` | layout.css |
| Feature-Karte | `.features-grid` > `.feature` (Icon-SVG, `h3`, `p`) | components.css |
| Produktkachel | `.tiles` > `a.tile` > `.tile-image` + `.tile-body` (`h3`, `.tile-cta`) | components.css |
| Schritte | `ol.steps` > `li` (`.step-number`, `h3`, `p`) | components.css |
| Kontaktkarte | `.contact-card` | components.css |
| Runder Icon-Knopf | `.icon-button` | layout.css |

Beispiel Abschnitt mit Kopf und Button:

```html
<section class="section">
  <div class="container">
    <div class="section-head reveal">
      <p class="eyebrow">Warenkorb</p>
      <h2>Deine Auswahl</h2>
      <p class="section-intro">Prüfe deine Artikel vor der Bestellung.</p>
    </div>
    <a href="#" class="button">Zur Kasse</a>
  </div>
</section>
```

Neue Bausteine, die mehr als eine Seite braucht, kommen nach Absprache in `components.css` und werden hier in die Tabelle eingetragen.

## 7. Bewegung und Hover

Die Seite soll lebendig wirken, aber nie hektisch.

- **Einblenden beim Scrollen**: `class="reveal"` an ein Element hängen. Für gestaffeltes Erscheinen zusätzlich `reveal-delay`, `reveal-delay-2` oder `reveal-delay-3`. Das Auslösen übernimmt `layout.js`.
- **Hover-Muster**, an denen sich neue Elemente orientieren:
  - Karten und Kacheln heben sich um 6–8 px (`translateY`), der Rahmen wird `--accent`.
  - Bilder in Kacheln zoomen leicht (`scale(1.05–1.1)`).
  - Icons dürfen sich drehen oder minimal wachsen (`scale(1.08–1.15)`).
  - Links in der Navigation bekommen einen von links wachsenden Unterstrich.
- **Übergänge** immer mit `var(--ease)` und 0,25–0,6 s. Keine harten, schnellen Sprünge.
- **Keine Laufbänder** (Marquee) und kein Blinken. Das Laufband oben wurde bewusst entfernt.
- **Barrierefreiheit**: `design.css` schaltet alle Animationen ab, wenn im Betriebssystem „Bewegung reduzieren“ aktiv ist. Das nicht aushebeln, z. B. nicht mit `!important` in Seiten-CSS.

## 8. Kopfbereich und Benutzermenü

- Kopfbereich mit Logo, Navigation, Benutzer-Icon und Warenkorb-Icon kommen unverändert aus `vorlage.html`.
- Das Benutzermenü wird von `layout.js` befüllt:
  - nicht angemeldet: „Anmelden“ und „Registrieren“
  - angemeldet: „Mein Konto“, „Meine Bestellungen“, „Persönliche Daten“, „Abmelden“
- **Aktueller Stand (Platzhalter):** Ob jemand angemeldet ist, wird nur simuliert. `?angemeldet=1` an der Adresse zeigt die angemeldete Ansicht. Die Links führen noch auf `#`. Wer die Stories für Login, Registrierung oder Konto umsetzt, ersetzt das durch echte Daten aus dem Backend.

## 9. Logo und Favicon

> **Pflicht:** Jede Seite von LaserFlow zeigt das Logo im Kopf- und Fußbereich und das Favicon in der Tableiste. Eine Seite ohne Logo oder Favicon ist nicht fertig (zählt zur Definition of Done für Frontend-Seiten).

Gewählt ist das Logo **„Lichtpunkt“**: Ein Laserstrahl fällt auf einen Punkt, Ringe breiten sich wie eine Gravur aus. Daneben steht der Schriftzug „Laser“ (Inter, dünn) + „Flow“ (Inter, fett, Akzentfarbe).

- **Auf der Website** steht das Logo als Inline-SVG mit der Klasse `.logo-mark` im Kopf- und Fußbereich (aus `vorlage.html` übernehmen). Die Farben kommen aus CSS (`color: var(--accent)`), die Styles stehen in `layout.css`. Die inneren Ringe „atmen“ langsam, beim Darüberfahren breiten sie sich aus.
- **Dateien** in `img/logo/`, alle mit transparentem Hintergrund:

| Datei | Wofür |
| --- | --- |
| `logo-auf-dunkel.svg` | Logo mit Schriftzug für dunkle Flächen (heller Text, Cyan) |
| `logo-auf-hell.svg` | Logo mit Schriftzug für helle Flächen (dunkler Text, dunkles Türkis `#1f8f8f`) |
| `favicon.svg` | Icon in der Tableiste; passt sich automatisch an helle und dunkle Browser an |
| `favicon-32.png` | Ersatz für Browser ohne SVG-Favicon |
| `apple-touch-icon.png` | Icon für den Homescreen auf dem Handy (mit dunklem Hintergrund, weil iOS keine Transparenz kann) |

- Jede Seite bindet die Favicons im `<head>` ein (steht schon in `vorlage.html`). Fehlt der Eintrag trotzdem, ergänzt `layout.js` das Favicon automatisch. Das ist nur ein Sicherheitsnetz, der Eintrag im `<head>` gehört trotzdem dazu.
- **Ausrichtung:** Der `viewBox` der Bildmarke ist `2 16 96 96`. Damit liegt der Mittelpunkt der Ringe genau in der Mitte, und das Icon sitzt auf einer Höhe mit dem Schriftzug. Den Wert nicht ändern, sonst rutscht das Icon nach unten.
- Auf weißem Grund nie `#97FFFF` für das Logo verwenden, das ist nicht lesbar. Dort `logo-auf-hell.svg` nehmen.
- Logo nicht verzerren, nicht umfärben und keinen Rahmen oder Kasten darum setzen.

## 10. Bilder und Icons

- Icons sind schlichte Linien-SVGs direkt im HTML (`stroke="currentColor"`, `stroke-width="1.6"`, ohne Füllung). Dadurch übernehmen sie automatisch die Textfarbe.
- Platzhalterbilder liegen in `img/` und sind als „Platzhalter“ beschriftet.
- Jedes `<img>` bekommt einen aussagekräftigen `alt`-Text.

## 11. Für Claude: So arbeitest du mit diesem Design

- Lies dieses Dokument, bevor du HTML oder CSS für LaserFlow schreibst.
- Neue Seiten entstehen immer aus `vorlage.html`. Kopf- und Fußbereich schreibst du nicht neu.
- Verwende ausschließlich die Variablen aus Abschnitt 4 und 5. Erfinde keine neuen Farben, Schriften oder Radien.
- Nutze zuerst die Bausteine aus Abschnitt 6. Seiteneigenes kommt in `css/<seite>.css` bzw. `js/<seite>.js`.
- `design.css`, `layout.css`, `components.css`, `layout.js` und `vorlage.html` sind gemeinsame Dateien. Ändere sie nur, wenn das Teammitglied bestätigt, dass es mit dem Team abgesprochen ist (siehe `CLAUDE.md`, Abschnitt 2).
- Bleib beim Tech Stack: HTML, CSS und JavaScript ohne Framework, keine UI-Bibliotheken.
- Bewegungen folgen Abschnitt 7.
- **Jede neue oder geänderte Seite muss Logo und Favicon enthalten** (Abschnitt 9). Übernimm beides unverändert aus `vorlage.html` bzw. `img/logo/`. Zeichne das Logo nicht neu und ändere den `viewBox` nicht. Fehlt es auf einer bestehenden Seite, weise das Teammitglied darauf hin.

## Bekannte Grenzen

- Die Seiten sind noch statisches HTML. Kopf- und Fußbereich stehen deshalb in jeder Seite einzeln. Ändert sich die Navigation, muss sie in allen Seiten angepasst werden. Sobald FastAPI die Seiten ausliefert, sollte das Team über ein gemeinsames Grundgerüst (z. B. Templates) entscheiden.
- Auf dem Handy ist die Navigation ausgeblendet, ein Burger-Menü fehlt noch.
- Die Schriften kommen von Google Fonts. Ohne Internet fällt die Seite auf Systemschriften zurück.
