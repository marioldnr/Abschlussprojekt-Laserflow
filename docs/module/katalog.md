# Modul: Produktkatalog und Warenkorb (Vorschau)

> Bereich: Besucher und Kunde (Use Cases „Produktkatalog ansehen“, „Produktdetails anzeigen“, „Artikel in den Warenkorb legen“, „Warenkorb bearbeiten“, `LaserFlow_Dokumentation.pdf`, Kapitel 1.2 und 1.4)
> Stand: **Nur Frontend, präsentierbare Vorschau.** Produktdaten stehen fest im JavaScript, der Warenkorb liegt im Browser. Backend (Katalog-Endpunkt, Tabelle `cart_items`) fehlt noch.
> Die zugehörige User Story und ihre Akzeptanzkriterien legt der PO fest; diese Datei beschreibt nur den Ist-Stand.

## Zweck

Besucher sehen alle Produkte als Kacheln (Foto, Name, Kategorie, Preis), können suchen, nach Kategorie filtern und sortieren. Ein Klick öffnet die Produktseite mit Bildergalerie, Beschreibung, Maßen und Material. Mit „In den Warenkorb“ landet das Produkt in einer Warenkorb-Leiste rechts (wie im Wireframe), dort lassen sich Mengen ändern und Artikel entfernen; der Gesamtbetrag wird sofort neu berechnet.

## Dateien

| Datei | Aufgabe |
| --- | --- |
| `frontend/katalog.html` | Seite „Produktkatalog anzeigen“ |
| `frontend/produkt.html` | Seite „Produktdetails anzeigen“, Aufruf mit `produkt.html?id=<id>` |
| `frontend/css/shop.css` | Styles für Katalog, Produktseite, Warenkorb-Leiste und die Produktfotos in Kacheln |
| `frontend/js/katalog.js` | Kacheln erzeugen, Suche, Kategorie-Knöpfe, Sortierung |
| `frontend/js/produkt.js` | Produkt aus `?id=` laden, Galerie (Pfeile, Punkte, Vorschaubilder, Pfeiltasten, Wischen), Menge, „In den Warenkorb“, weitere Produkte |
| `frontend/js/startseite-produkte.js` | Produktkacheln auf der Startseite (`index.html#produkte`) |
| `frontend/js/modules/products.js` | Produktliste (Platzhalter-Daten), `formatPrice`, `formatDimensions`, `findProduct`, `filterProducts`, `listCategories` |
| `frontend/js/modules/cart.js` | Warenkorb-Logik ohne DOM: hinzufügen, Menge ändern, entfernen, Summe, Speichern im Browser |
| `frontend/js/modules/cart-drawer.js` | Warenkorb-Leiste: wird per JavaScript erzeugt und mit dem Warenkorb-Icon im Kopfbereich verbunden |
| `frontend/img/produkte/*.webp` | freigestellte Produktfotos (1200 × 1200 px), erstes Bild = Titelbild |
| `frontend/tests/products.test.js`, `frontend/tests/cart.test.js` | Tests (`npm test` im Ordner `frontend/`) |

`index.html`: Die Platzhalter-Kacheln im Abschnitt „Unsere Produkte“ wurden durch die echten Produkte und eine Kachel „Alle Produkte“ ersetzt, „Produkte entdecken“ führt auf `katalog.html`.

## Ablauf

1. Seite lädt ihr Skript als ES-Modul (nur über Webserver, z. B. Live Server oder FastAPI).
2. Das Skript ruft `initCartDrawer()` auf: Warenkorb aus `localStorage` (`laserflow.cart`) lesen, Leiste anhängen, Zahl am Icon setzen.
3. Katalog/Startseite erzeugen die Kacheln aus `PRODUCTS`. Texte werden per `textContent` gesetzt, damit spätere Backend-Daten nie als HTML ausgeführt werden.
4. Produktseite: `findProduct(params.get("id"))`. Unbekannte oder ungültige ID → Hinweis „Dieses Produkt gibt es nicht“ mit Link zum Katalog.
5. „In den Warenkorb“ → `addToCart(id, menge)` → `cart.js` rechnet, speichert, Leiste öffnet sich.

## Bewusste Entscheidungen

- **Felder wie in der Tabelle `products`** (`price_cent`, `width_mm` …), damit der Wechsel aufs Backend nur die Datenquelle tauscht.
- **Preise in Cent**, Anzeige erst bei der Ausgabe mit `formatPrice` (wie im Backend).
- **Im Warenkorb stehen nur `productId` und `quantity`, kein Preis.** Der Preis wird immer aus den Produktdaten gelesen, so zeigt der Warenkorb nie einen alten Preis.
- **Höchstmenge 20 pro Position** (`MAX_QUANTITY`) gegen Tippfehler.
- **Warenkorb-Leiste per JavaScript**, damit `vorlage.html` und `layout.js` (gemeinsame Dateien) unverändert bleiben.
- **Produktfotos**: Hintergrund automatisch entfernt (OpenCV GrabCut), auf einen dunklen, warmen Verlauf passend zu `--bg`/`--surface` gesetzt, mit weichem Schatten; quadratisch 1200 px, WebP.

## Erweitern

- **Neues Produkt (jetzt):** Eintrag in `PRODUCTS` ergänzen (eindeutige `id`), Fotos nach `img/produkte/<slug>-1.webp` usw. legen.
- **Auf Backend umstellen:** Endpunkt `GET /api/products` (und `GET /api/products/{id}`) im Modul `app/catalog` (Router → Service), Ladefunktion in `api-client.js`; in `katalog.js`, `produkt.js` und `startseite-produkte.js` die Liste laden statt `PRODUCTS` zu lesen. Ausgeblendete Produkte (`is_hidden`) liefert der Endpunkt nicht aus; `is_sold_out` zeigt die Seite schon an (Schild „Ausverkauft“, Knopf gesperrt).
- **Warenkorb ins Backend:** `loadCart`/`saveCart` durch API-Aufrufe auf `cart_items` ersetzen, die Rechenfunktionen bleiben.

## Tests

`npm test` im Ordner `frontend/`: `products.test.js` (Preisformat, Maße, Suche, Filter, Sortierung, ungültige IDs, Datenprüfung) und `cart.test.js` (Hinzufügen, Mengen, Grenzen, Summe, kaputte gespeicherte Daten).

## Bekannte Grenzen

- Preise, Maße und Texte sind **Platzhalter** und werden im Team festgelegt.
- Produktdaten fest im JavaScript, noch kein Katalog-Endpunkt.
- Warenkorb nur im Browser (`localStorage`), nicht am Konto; „Zur Kasse“ ist noch gesperrt.
- Nur Seiten, die `cart-drawer.js` laden (Startseite, Katalog, Produktseite), zeigen die richtige Zahl am Warenkorb-Icon und öffnen die Leiste. Auf den übrigen Seiten bleibt das Icon bei „0“. Dauerhafte Lösung: Warenkorb-Anzeige in `layout.js` aufnehmen (gemeinsame Datei, nach Absprache).
- Der Menüpunkt „Produkte“ im Kopfbereich zeigt weiter auf `index.html#produkte`; ein eigener Link zum Katalog bräuchte eine Änderung an `vorlage.html` und allen Seiten (gemeinsam).
- Das X-Wing-Modell ist eine Star-Wars-Figur. Für die Schul-Demo unproblematisch, für einen echten Verkauf bräuchte es eine Lizenz.
