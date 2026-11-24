# Bild-Upload

> Zuletzt aktualisiert: 24.11.2026 · US04 (Task 1 und 2) · Marcus
> Vorlage nicht verändern – Kopie als `docs/module/<bereich>.md` anlegen. Abschnitte, die (noch) nicht zutreffen, mit „–“ füllen statt löschen.

## Zweck

Kunden laden ein eigenes Bild hoch, das auf ein Produkt graviert werden soll. Das Modul prüft die Datei (Typ und Größe), speichert das Original im Bildspeicher und legt dazu einen Eintrag in `customer_images` an. Jeder Kunde sieht nur seine eigenen Bilder.

## Zugehörige User Stories

| Story | Titel | Status |
|---|---|---|
| US04 | Bild hochladen und prüfen | in Arbeit (Task 1 Upload und Task 2 Dateiprüfung umgesetzt) |

## Ablauf

1. Der Kunde schickt das Bild als Body an `POST /api/images?product_id=<id>` (`app/images/router.py`).
2. Der Router prüft über `get_current_user`, ob jemand angemeldet ist (sonst 401). Ist die Datei laut `Content-Length` größer als 5 MB, bricht er sofort ab, ohne sie zu lesen.
3. Der Router ruft `upload_image()` in `app/images/service.py` auf. Der Service:
   1. prüft, ob es das Produkt gibt und ob es sichtbar ist (sonst 404),
   2. prüft die Datei mit `validate_file()`: nicht leer, höchstens 5 MB, JPEG oder PNG (sonst 422),
   3. speichert sie mit `storage.save_file()` unter `customer-images/<user_id>-<zufall>.<jpg|png>`,
   4. legt eine Zeile in `customer_images` mit Status `uploaded` an.
4. Der Router gibt das Bild als JSON zurück (201). Das Original lädt das Frontend über `original_url`.

## Wichtige Dateien

| Datei | Aufgabe |
|---|---|
| `app/images/router.py` | Endpunkte, reicht nur an den Service weiter |
| `app/images/service.py` | Prüfung, Speichern, Rechteprüfung „nur eigene Bilder“, Fehlermeldungen |
| `app/images/schemas.py` | Antwortformat `ImageResponse` |
| `app/images/models.py` | Tabelle `customer_images` (gab es schon, unverändert) |
| `app/storage.py` | Bildspeicher (Neon Object Storage oder lokal `uploads/`) |
| `app/accounts/account_service.py` | `_anonymize` löscht Kundenbilder ohne Bestellung beim Konto-Löschen (US10), ebenfalls über `storage.delete_file` |
| `tests/test_images_service.py` | Tests für Prüfung und Service |
| `tests/test_images_router.py` | Tests der Endpunkte über HTTP |

## Endpunkte

Alle nur für angemeldete Konten, sonst **401**.

| Methode | Pfad | Zweck | Fehlerfälle (Statuscode) |
|---|---|---|---|
| POST | `/api/images?product_id=<id>` | Bild hochladen (Bild als Body, kein Formular) | 404 Produkt fehlt/ausgeblendet, 422 Datei leer, über 5 MB oder kein JPEG/PNG, 422 `product_id` fehlt |
| GET | `/api/images/{id}` | Daten zum eigenen Bild (JSON) | 404 Bild fehlt oder gehört jemand anderem |
| GET | `/api/images/{id}/original` | eigenes Originalbild als Datei | 404 Bild fehlt, gehört jemand anderem oder Datei fehlt im Speicher |

Antwort von POST und GET `/api/images/{id}`:

```json
{"id": 1, "product_id": 3, "status": "uploaded", "created_at": "2026-11-24T10:00:00", "original_url": "/api/images/1/original"}
```

Fehler bei der Datei (422) haben dasselbe Format wie die Formularfehler im Konto-Modul:

```json
{"detail": [{"loc": ["body", "image"], "msg": "Bitte wähle ein Bild im Format JPEG oder PNG."}]}
```

## Datenmodell

- **Datenbank:** Tabelle `customer_images`. Beim Upload werden `user_id`, `product_id`, `original_path` (der Schlüssel im Bildspeicher) und `status = "uploaded"` gesetzt. Die übrigen Spalten (`background_removed_path`, `processed_path`, `chosen_variant`, `was_upscaled`, `quality_warning`) bleiben leer, sie gehören zu späteren Schritten (US04 Task 3, US05, US06).
- **Bildspeicher:** die Datei selbst unter `customer-images/<user_id>-<16 Hex-Zeichen>.<jpg|png>`.

## Bewusste Entscheidungen

- **Bild als Body statt Formular (multipart):** wie beim Profilbild (`PUT /api/account/avatar`). FastAPI braucht dafür kein Zusatzpaket (`python-multipart`).
- **Typ an den ersten Bytes erkennen („Magic Bytes“):** Dateiendung und `Content-Type` schickt der Browser mit, beides lässt sich fälschen.
- **Nur JPEG und PNG:** so steht es im Akzeptanzkriterium von US04. WebP ist beim Profilbild erlaubt, hier nicht.
- **Genau 5 MB sind erlaubt**, ab 5 MB + 1 Byte wird abgelehnt (`MAX_BYTES` in `service.py`). Die Grenze steht im Modul, nicht in `config.py`, damit für Task 1 und 2 keine gemeinsame Datei geändert werden musste.
- **Fremde Bilder geben 404 statt 403:** So erfährt niemand, ob es ein Bild mit dieser Nummer gibt.
- **Speicher-Schlüssel wird nicht ausgegeben:** Das Frontend bekommt nur `original_url`. So läuft jeder Abruf durch die Rechteprüfung.
- **Ausgeblendete Produkte gelten als nicht vorhanden** (404), passend zu `Product.is_hidden`.

## Tests

- Ausführen: `python -m pytest tests/test_images_service.py tests/test_images_router.py`
- Abgedeckt:
  - **Normalfall:** PNG und JPEG hochladen, Eintrag mit Status `uploaded`, Datei im Speicher, eigenes Bild abrufen.
  - **Ungültige Eingaben:** leere Datei, PDF, WebP, GIF, SVG, abgeschnittener PNG-Anfang, fehlende `product_id`, unbekanntes oder ausgeblendetes Produkt. Ungültige Dateien werden nicht gespeichert.
  - **Grenzfälle:** genau 5 MB erlaubt, 5 MB + 1 Byte abgelehnt. Zwei Uploads bekommen verschiedene Schlüssel.
  - **Rechte:** ohne Anmeldung 401 auf allen Endpunkten, fremdes Bild 404, fehlende Datei im Speicher 404.

## Bekannte Grenzen

- **Keine Qualitätsprüfung:** Auflösung, Kontrast und Schärfe prüft das Modul noch nicht (US04 Task 3, dafür kommen Pillow und NumPy dazu).
- **Keine Oberfläche:** Es gibt noch keinen Upload-Knopf im Frontend (US04 Task 4).
- **Produkt-IDs:** Der Upload braucht ein Produkt in der Datenbank. Solange die Katalog-API fehlt, kennt das Frontend nur fest eingetragene Produkte.
- **Alte Uploads werden nicht aufgeräumt:** Lädt ein Kunde mehrmals hoch, bleiben alle Bilder gespeichert.

## So erweiterst du das Modul

- **Neuen Dateityp zulassen:** in `detect_image_type()` die ersten Bytes des Formats ergänzen, `MSG_TYPE` anpassen, Test in `tests/test_images_service.py` (`test_png_and_jpeg_are_accepted`) ergänzen und den Fall aus `test_wrong_type_is_rejected` entfernen.
- **Größengrenze ändern:** `MAX_BYTES` in `app/images/service.py` ändern. Die Meldung `MSG_SIZE` und die Router-Vorabprüfung passen sich automatisch an.
- **Qualitätsprüfung (Task 3) einbauen:** eigene Funktion im Service, aufgerufen in `upload_image()` nach `validate_file()`. Ergebnis in `quality_warning` speichern.
