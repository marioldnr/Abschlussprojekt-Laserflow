# Modul: Produktkatalog und Warenkorb (Vorschau)

> Bereich: Besucher und Kunde (Use Cases „Produktkatalog ansehen“, „Produktdetails anzeigen“, „Artikel in den Warenkorb legen“, „Warenkorb bearbeiten“, `LaserFlow_Dokumentation.pdf`, Kapitel 1.2 und 1.4)
> Stand: Produkte kommen aus der Datenbank (Katalog-Endpunkte, US01). Der Warenkorb liegt noch im Browser; die Tabelle `cart_items` und der Warenkorb am Konto fehlen noch.
> Die zugehörige User Story und ihre Akzeptanzkriterien legt der PO fest; diese Datei beschreibt nur den Ist-Stand.

## Zweck

Besucher sehen alle Produkte als Kacheln (Foto, Name, Kategorie, Preis), können suchen, nach Produktart filtern und sortieren. Ein Klick öffnet die Produktseite mit Bildergalerie, Beschreibung, Maßen und Material. Mit „In den Warenkorb“ landet das Produkt in einer Warenkorb-Leiste rechts (wie im Wireframe), dort lassen sich Mengen ändern und Artikel entfernen; der Gesamtbetrag wird sofort neu berechnet.

## Dateien

| Datei | Aufgabe |
| --- | --- |
| `frontend/katalog.html` | Seite „Produktkatalog anzeigen“ |
| `frontend/produkt.html` | Seite „Produktdetails anzeigen“, Aufruf mit `produkt.html?id=<id>` |
| `frontend/css/shop.css` | Styles für Katalog, Produktseite, Warenkorb-Leiste und die Produktfotos in Kacheln |
| `frontend/js/katalog.js` | Kacheln erzeugen, Suche, Kategorie-Knöpfe, Sortierung |
| `frontend/js/produkt.js` | Produkt aus `?id=` laden, Galerie (Pfeile, Punkte, Vorschaubilder, Pfeiltasten, Wischen), Menge, „In den Warenkorb“, weitere Produkte |
| `frontend/js/startseite-produkte.js` | Produktkacheln auf der Startseite (`index.html#produkte`) |
| `frontend/js/modules/products.js` | Lädt die Produkte per `loadProducts()` vom Backend in `PRODUCTS`, `toViewProduct` (Produktart → Kategorie), `formatPrice`, `formatDimensions`, `findProduct`, `filterProducts`, `listCategories` |
| `app/catalog/router.py` | Endpunkte unter `/api/products` (nur HTTP) |
| `app/catalog/service.py` | Logik: sichtbare Produkte lesen, alle Produkte für die Verwaltung lesen, ausverkauft markieren, ausblenden/einblenden, Produkt mit Bildern anlegen, erlaubte Produktarten |
| `app/catalog/schemas.py` | Form der Antwort (nur öffentliche Felder), Kurzbeschreibung = erster Satz |
| `app/catalog/models.py` | Tabellen `products` und `product_images` (gemeinsame Datei, hier nur benutzt) |
| `scripts/seed_db.py` | legt die Demoprodukte an (`DEMO_PRODUCTS`, `python -m scripts.seed_db`) |
| `frontend/js/modules/cart.js` | Warenkorb-Logik ohne DOM: hinzufügen, Menge ändern, entfernen, Summe, Speichern im Browser |
| `frontend/js/modules/cart-drawer.js` | Warenkorb-Leiste: wird per JavaScript erzeugt und mit dem Warenkorb-Icon im Kopfbereich verbunden |
| `frontend/img/produkte/*.webp` | freigestellte Produktfotos (1200 × 1200 px), erstes Bild = Titelbild; `gravurplatte-platzhalter.svg` für die Gravurplatte |
| `frontend/tests/products.test.js`, `frontend/tests/cart.test.js` | Tests (`npm test` im Ordner `frontend/`) |
| `tests/test_catalog_service.py`, `tests/test_catalog_router.py` | Backend-Tests (`pytest`) |
| `frontend/produkte-verwalten.html` | Seite „Produkte verwalten“ für Mitarbeiter und Admin (US14, Anfang) |
| `frontend/js/produkte-verwalten.js` | Seite „Produkte verwalten“: Liste laden, Knöpfe für ausverkauft und ausblenden, Suche und Filter |
| `frontend/css/produkte-verwalten.css` | Styles der Seite „Produkte verwalten“ |
| `frontend/js/modules/product-admin.js` | Filter, Suche und Status-Texte der Verwaltungsliste (ohne DOM) |
| `frontend/tests/product-admin.test.js` | Tests für `product-admin.js` (`npm test` im Ordner `frontend/`) |

`index.html`: Die Platzhalter-Kacheln im Abschnitt „Unsere Produkte“ wurden durch die echten Produkte und eine Kachel „Alle Produkte“ ersetzt, „Produkte entdecken“ führt auf `katalog.html`.

## Ablauf

1. Seite lädt ihr Skript als ES-Modul (nur über Webserver, z. B. Live Server oder FastAPI).
2. Das Skript lädt zuerst die Produkte (`loadProducts()`, `GET /api/products`), danach ruft es `initCartDrawer()` auf: Warenkorb aus `localStorage` (`laserflow.cart`) lesen, Leiste anhängen, Zahl am Icon setzen.
3. `loadProducts()` füllt `PRODUCTS`. Katalog und Startseite erzeugen die Kacheln daraus. Texte werden per `textContent` gesetzt, damit spätere Backend-Daten nie als HTML ausgeführt werden.
4. Produktseite: `findProduct(params.get("id"))`. Unbekannte oder ungültige ID → Hinweis „Dieses Produkt gibt es nicht“ mit Link zum Katalog.
5. „In den Warenkorb“ → `addToCart(id, menge)` → `cart.js` rechnet, speichert, Leiste öffnet sich.

## Bewusste Entscheidungen

- **Felder wie in der Tabelle `products`** (`price_cent`, `width_mm` …), damit der Wechsel aufs Backend nur die Datenquelle tauscht.
- **Preise in Cent**, Anzeige erst bei der Ausgabe mit `formatPrice` (wie im Backend).
- **Im Warenkorb stehen nur `productId` und `quantity`, kein Preis.** Der Preis wird immer aus den Produktdaten gelesen, so zeigt der Warenkorb nie einen alten Preis.
- **Höchstmenge 20 pro Position** (`MAX_QUANTITY`) gegen Tippfehler.
- **Warenkorb-Leiste per JavaScript**, damit `vorlage.html` und `layout.js` (gemeinsame Dateien) unverändert bleiben.
- **Filter nach Produktart statt Kategorie**: Es gibt keine Kategorie-Spalte in der Datenbank. Die Anzeige-Kategorie leitet sich aus `product_type` ab (`customer_image` → „Mit eigenem Bild“, sonst „Fertige Produkte“). Deshalb ist keine Migration nötig.
- **Material als Konstante** (`MATERIAL`, US14): Es ist für alle Produkte gleich und steht deshalb nicht in der Datenbank.
- **Interne Felder werden nicht ausgeliefert**: CAD-Vorlage, Laserprogramm, Laser-Einstellungen, Ausblende-Flag und Anlagedatum bleiben im Backend (`schemas.py`).
- **`PRODUCTS` bleibt als Zwischenspeicher**: Die Warenkorb-Leiste (`cart-drawer.js`, US07) liest weiter über `findProduct` aus `PRODUCTS`. Deshalb musste sie nicht geändert werden.
- **Kurzbeschreibung = erster Satz der Beschreibung** (`short_description_of`): Es gibt keine eigene Spalte. Siehe Bekannte Grenzen.
- **Ladefehler werden nicht festgehalten**: Schlägt `loadProducts()` fehl, löscht es seinen Merker, damit der nächste Aufruf erneut lädt.
- **Produkte mit eigenem Bild** (`has_customer_image`) kommen ohne Upload nicht in den Warenkorb. Der Knopf zeigt bis US04 nur einen Hinweis.
- **Produktfotos**: Hintergrund automatisch entfernt (OpenCV GrabCut), auf einen dunklen, warmen Verlauf passend zu `--bg`/`--surface` gesetzt, mit weichem Schatten; quadratisch 1200 px, WebP.

## Produkte verwalten (Mitarbeiter und Admin, US14, Anfang)

Mitarbeiter und Admins öffnen `produkte-verwalten.html` über „Produkte verwalten“ im Benutzermenü. Die Seite zeigt alle Produkte, auch die ausgeblendeten, mit Vorschaubild, Produktart, Preis und Status-Plaketten („Ausverkauft“, „Ausgeblendet“). Es gibt eine Suche nach Name und die Filter „Alle“, „Verfügbar“, „Ausverkauft“ und „Ausgeblendet“ (Verfügbar = sichtbar und nicht ausverkauft). Je Produkt zwei Knöpfe:

- „Als ausverkauft markieren“ bzw. „Wieder verfügbar“
- „Ausblenden“ (mit Rückfrage) bzw. „Wieder einblenden“

Endpunkte (alle nur für angemeldete Mitarbeiter und Admins):

| Endpunkt | Aufgabe | Antworten |
| --- | --- | --- |
| `GET /api/products/manage` | alle Produkte inkl. ausgeblendete, mit Feld `is_hidden` | 200 · 401 · 403 |
| `PUT /api/products/{id}/sold-out` | ausverkauft markieren oder aufheben, auch bei ausgeblendeten Produkten | 200 · 401 · 403 · 404 · 422 |
| `PUT /api/products/{id}/hidden` | ausblenden (`is_hidden: true`) oder wieder einblenden (`false`) | 200 · 401 · 403 · 404 · 422 |

Bewusste Entscheidungen:

- **Ausblenden ist ein Flag, kein Löschen.** Es wird nur `is_hidden` gesetzt. Alte Bestellungen zeigen weiter auf das Produkt. Wieder einblenden ist jederzeit möglich.
- **Ausverkauft und ausgeblendet sind unabhängig.** Ein ausgeblendetes Produkt kann ausverkauft sein; nach dem Einblenden bleibt es ausverkauft.
- **`GET /manage` steht vor `GET /{product_id}`** im Router. Sonst würde FastAPI „manage“ als Produkt-ID lesen und mit 422 antworten.
- **Kunden sehen unverändert** nur `GET /api/products` und `GET /api/products/{id}` ohne ausgeblendete Produkte und ohne `is_hidden`. Die Verwaltung bekommt ein eigenes Antwortformat (`ManagedProductResponse`).
- **Die Seite ist nur Komfort.** Geschützt wird im Backend (`require_employee`). Der Link im Benutzermenü erscheint für Mitarbeiter und Admins (`layout.js`).

## Erweitern

- **Neues Produkt (jetzt):** Eintrag in `DEMO_PRODUCTS` (`scripts/seed_db.py`) ergänzen und `python -m scripts.seed_db` starten; Fotos nach `frontend/img/produkte/` legen, in der Datenbank steht nur der Pfad. Eine Oberfläche zum Anlegen fehlt noch (US14).
- **Neues Feld in der Antwort:** in `app/catalog/schemas.py` (`ProductResponse`, `from_product`) ergänzen. CAD-Pfade und Laserdaten bleiben intern. Ausgeblendete Produkte (`is_hidden`) liefert der Endpunkt nicht aus; `is_sold_out` zeigt die Seite an (Schild „Ausverkauft“, Knopf gesperrt).
- **Warenkorb ins Backend:** `loadCart`/`saveCart` durch API-Aufrufe auf `cart_items` ersetzen, die Rechenfunktionen bleiben.

## Tests

`npm test` im Ordner `frontend/`: `products.test.js` (Preisformat, Maße ohne Tiefe, Umwandlung aus der API, Suche, Filter, Sortierung, ungültige IDs, Laden mit Fehlerwiederholung), `cart.test.js` (Hinzufügen, Mengen, Grenzen, Summe, kaputte gespeicherte Daten) und `product-admin.test.js` (Filter der Verwaltungsliste, Suche, Status-Plaketten, Produktart).

Backend: `python -m pytest -q` mit `tests/test_catalog_service.py` (Anlegen, Sichtbarkeit, Ausverkauft, Seed zweimal) und `tests/test_catalog_router.py` (Zugriff ohne Anmeldung, Kunde 403, Mitarbeiter, Felder der Antwort).

## Bekannte Grenzen

- Preise, Maße und Texte sind **Platzhalter** und werden im Team festgelegt.
- Bild-Upload („Bild hochladen“) ist nur ein Platzhalter bis US04. Die Gravurplatte ist ein Platzhalterprodukt.
- Die Verwaltungsseite kann bisher nur ausverkauft markieren und ausblenden. Anlegen, Bearbeiten (Name, Preis, Maße, Beschreibung) und Bilder fehlen noch (Rest von US14).
- Die Verwaltungsseite ist nicht durch automatische Browser-Tests abgedeckt. Geprüft sind die Filter und Status-Texte (`product-admin.test.js`) sowie die Endpunkte (`pytest`).
- Produktbilder liegen im Frontend-Ordner `frontend/img/produkte` und nicht im gemeinsamen Bildspeicher (geplant, siehe `docs/module/bildspeicher.md`).
- Die Kurzbeschreibung ist der erste Satz der Beschreibung. Damit er auf der Produktseite nicht zweimal steht, zeigt `products.js` unter „Beschreibung“ den Text ohne diesen Satz (`long_description`). Sauber wäre eine eigene Spalte; das ist eine Model-Änderung und braucht Absprache im Team.
- Hat ein Produkt kein Foto, zeigen Katalog und Produktseite das LaserFlow-Logo als Ersatzbild (`FALLBACK_IMAGE`).
- Ein Produkt ohne Bild bekommt in Katalog und Startseite ein kaputtes Bild, weil das Frontend `images[0]` ungeprüft benutzt.
- Warenkorb nur im Browser (`localStorage`), nicht am Konto; „Zur Kasse“ ist noch gesperrt.
- Nur Seiten, die `cart-drawer.js` laden (Startseite, Katalog, Produktseite), zeigen die richtige Zahl am Warenkorb-Icon und öffnen die Leiste. Auf den übrigen Seiten bleibt das Icon bei „0“. Dauerhafte Lösung: Warenkorb-Anzeige in `layout.js` aufnehmen (gemeinsame Datei, nach Absprache).
- Der Menüpunkt „Produkte“ im Kopfbereich zeigt weiter auf `index.html#produkte`; ein eigener Link zum Katalog bräuchte eine Änderung an `vorlage.html` und allen Seiten (gemeinsam).
- Das X-Wing-Modell ist eine Star-Wars-Figur. Für die Schul-Demo unproblematisch, für einen echten Verkauf bräuchte es eine Lizenz.
