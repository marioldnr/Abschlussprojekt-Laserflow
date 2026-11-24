# Bild-Upload

> Zuletzt aktualisiert: 24.11.2026 · US04 (Task 1 bis 3) · Marcus
> Vorlage nicht verändern – Kopie als `docs/module/<bereich>.md` anlegen. Abschnitte, die (noch) nicht zutreffen, mit „–“ füllen statt löschen.

## Zweck

Kunden laden ein eigenes Bild hoch, das auf ein Produkt graviert werden soll. Das Modul prüft die Datei (Typ und Größe) und die Bildqualität (Auflösung hart, Kontrast und Schärfe als Warnung), speichert das Original im Bildspeicher und legt dazu einen Eintrag in `customer_images` an. Jeder Kunde sieht nur seine eigenen Bilder.

## Zugehörige User Stories

| Story | Titel | Status |
|---|---|---|
| US04 | Bild hochladen und prüfen | in Arbeit (Task 1 Upload, Task 2 Dateiprüfung, Task 3 Bildqualität umgesetzt) |

## Ablauf

1. Der Kunde schickt das Bild als Body an `POST /api/images?product_id=<id>` (`app/images/router.py`).
2. Der Router prüft über `get_current_user`, ob jemand angemeldet ist (sonst 401). Ist die Datei laut `Content-Length` größer als 5 MB, bricht er sofort ab, ohne sie zu lesen.
3. Der Router ruft `upload_image()` in `app/images/service.py` auf. Der Service:
   1. prüft, ob es das Produkt gibt und ob es sichtbar ist (sonst 404),
   2. prüft, ob das Produkt einen Gravurbereich hat (sonst 404 „Für dieses Produkt ist kein Bild-Upload möglich.“),
   3. prüft die Datei mit `validate_file()`: nicht leer, höchstens 5 MB, JPEG oder PNG (sonst 422),
   4. prüft die Bildqualität mit `quality.check_quality()` (siehe unten). Zu kleine oder nicht lesbare Bilder: 422,
   5. speichert sie mit `storage.save_file()` unter `customer-images/<user_id>-<zufall>.<jpg|png>`,
   6. legt eine Zeile in `customer_images` mit Status `uploaded` und ggf. Warnungen in `quality_warning` an.
4. Der Router gibt das Bild als JSON zurück (201), inklusive Warnungen und `needs_upscale`. Das Original lädt das Frontend über `original_url`.

### Qualitätsprüfung (`app/images/quality.py`)

| Prüfung | Regel | Folge |
|---|---|---|
| Zielgröße | (Gravurbereich − 2 × 1 mm Rand) × 10 Pixel pro mm, z. B. 80 × 60 mm → 780 × 580 Pixel | – |
| Faktor ≤ 1 | Bild ist groß genug | ok |
| Faktor über 1 bis 4 | Bild ist kleiner, KI kann es hochskalieren | gespeichert, `needs_upscale: true` (US06 skaliert hoch) |
| Faktor über 4 | auch Hochskalieren reicht nicht | 422 „… mindestens 195 × 145 Pixel.“ |
| Kontrast | Standardabweichung der Grauwerte unter 25 | Warnung |
| Schärfe | Varianz des Laplace-Filters unter 30, gemessen bei Zielgröße | Warnung |

Faktor = um wie viel das Bild vergrößert werden müsste; die knappere Seite zählt. Handyfotos werden vorher laut EXIF gedreht.

## Wichtige Dateien

| Datei | Aufgabe |
|---|---|
| `app/images/router.py` | Endpunkte, reicht nur an den Service weiter |
| `app/images/service.py` | Prüfung, Speichern, Rechteprüfung „nur eigene Bilder“, Fehlermeldungen |
| `app/images/quality.py` | Qualitätsprüfung (Auflösung, Kontrast, Schärfe), kennt weder Datenbank noch Speicher |
| `app/images/schemas.py` | Antwortformate `ImageResponse` und `UploadResponse` |
| `app/images/models.py` | Tabelle `customer_images` (gab es schon, unverändert) |
| `app/storage.py` | Bildspeicher (Neon Object Storage oder lokal `uploads/`) |
| `app/accounts/account_service.py` | `_anonymize` löscht Kundenbilder ohne Bestellung beim Konto-Löschen (US10), ebenfalls über `storage.delete_file` |
| `tests/test_images_service.py` | Tests für Prüfung und Service |
| `tests/test_images_router.py` | Tests der Endpunkte über HTTP |
| `tests/test_images_quality.py` | Tests der Qualitätsprüfung (Testbilder werden im Test erzeugt) |

## Endpunkte

Alle nur für angemeldete Konten, sonst **401**.

| Methode | Pfad | Zweck | Fehlerfälle (Statuscode) |
|---|---|---|---|
| POST | `/api/images?product_id=<id>` | Bild hochladen (Bild als Body, kein Formular) | 404 Produkt fehlt/ausgeblendet oder ohne Gravurbereich, 422 Datei leer, über 5 MB, kein JPEG/PNG, nicht lesbar oder zu klein (Faktor über 4), 422 `product_id` fehlt |
| GET | `/api/images/{id}` | Daten zum eigenen Bild (JSON) | 404 Bild fehlt oder gehört jemand anderem |
| GET | `/api/images/{id}/original` | eigenes Originalbild als Datei | 404 Bild fehlt, gehört jemand anderem oder Datei fehlt im Speicher |

Antwort von GET `/api/images/{id}`:

```json
{"id": 1, "product_id": 3, "status": "uploaded", "created_at": "2026-11-24T10:00:00", "quality_warnings": [], "original_url": "/api/images/1/original"}
```

POST liefert dasselbe plus `"needs_upscale": true|false`.

Fehler bei der Datei (422) haben dasselbe Format wie die Formularfehler im Konto-Modul:

```json
{"detail": [{"loc": ["body", "image"], "msg": "Bitte wähle ein Bild im Format JPEG oder PNG."}]}
```

## Datenmodell

- **Datenbank:** Tabelle `customer_images`. Beim Upload werden `user_id`, `product_id`, `original_path` (der Schlüssel im Bildspeicher) und `status = "uploaded"` gesetzt. `quality_warning` enthält die Warnungen als Text, mehrere mit „; “ getrennt (leer, wenn alles passt). Die übrigen Spalten (`background_removed_path`, `processed_path`, `chosen_variant`, `was_upscaled`) bleiben leer, sie gehören zu US05 und US06.
- **Bildspeicher:** die Datei selbst unter `customer-images/<user_id>-<16 Hex-Zeichen>.<jpg|png>`.

## Bewusste Entscheidungen

- **Bild als Body statt Formular (multipart):** wie beim Profilbild (`PUT /api/account/avatar`). FastAPI braucht dafür kein Zusatzpaket (`python-multipart`).
- **Typ an den ersten Bytes erkennen („Magic Bytes“):** Dateiendung und `Content-Type` schickt der Browser mit, beides lässt sich fälschen.
- **Nur JPEG und PNG:** so steht es im Akzeptanzkriterium von US04. WebP ist beim Profilbild erlaubt, hier nicht.
- **Genau 5 MB sind erlaubt**, ab 5 MB + 1 Byte wird abgelehnt (`MAX_BYTES` in `service.py`). Die Grenze steht im Modul, nicht in `config.py`, damit für Task 1 und 2 keine gemeinsame Datei geändert werden musste.
- **Fremde Bilder geben 404 statt 403:** So erfährt niemand, ob es ein Bild mit dieser Nummer gibt.
- **Speicher-Schlüssel wird nicht ausgegeben:** Das Frontend bekommt nur `original_url`. So läuft jeder Abruf durch die Rechteprüfung.
- **Ausgeblendete Produkte gelten als nicht vorhanden** (404), passend zu `Product.is_hidden`.
- **Grenzwerte der Qualitätsprüfung** (mit Mario am 24.11.2026, aus dem KI-Plan vom 17.11.): 10 Pixel pro mm, 1 mm Rand, höchstens Faktor 4. Kontrast 25 statt der geplanten 30, weil gute Fotos im Test bei 31–32 lagen. Schärfe 30 statt 100, gemessen bei Zielgröße.
- **Schärfe bei Zielgröße messen:** Die Laplace-Varianz hängt stark von der Bildgröße ab (dasselbe scharfe Foto: 1132 bei 512 px, 10 bei 2048 px). Ohne Skalieren würde fast jedes Handyfoto als unscharf gewarnt. Nicht „vereinfachen“, ohne die Grenzwerte neu zu prüfen.
- **`needs_upscale` wird nicht gespeichert:** keine eigene Spalte, also keine Migration. US06 rechnet den Faktor aus Bild und Produkt selbst neu aus.
- **Produkt ohne Gravurbereich → 404** „Für dieses Produkt ist kein Bild-Upload möglich.“ Geprüft vor der Datei, weil es am Produkt liegt, nicht am Bild.
- **Zuerst alles prüfen, dann speichern:** Abgelehnte Bilder landen nie im Bildspeicher.

## Tests

- Ausführen: `python -m pytest tests/test_images_service.py tests/test_images_router.py tests/test_images_quality.py`
- Abgedeckt:
  - **Normalfall:** PNG und JPEG hochladen, Eintrag mit Status `uploaded`, Datei im Speicher, eigenes Bild abrufen.
  - **Ungültige Eingaben:** leere Datei, PDF, WebP, GIF, SVG, abgeschnittener PNG-Anfang, fehlende `product_id`, unbekanntes oder ausgeblendetes Produkt. Ungültige Dateien werden nicht gespeichert.
  - **Grenzfälle:** genau 5 MB erlaubt, 5 MB + 1 Byte abgelehnt. Zwei Uploads bekommen verschiedene Schlüssel.
  - **Rechte:** ohne Anmeldung 401 auf allen Endpunkten, fremdes Bild 404, fehlende Datei im Speicher 404.
  - **Qualität:** Zielgröße 780 × 580, genau Faktor 4 erlaubt, 1 Pixel weniger abgelehnt (mit Mindestgröße in der Meldung), knappere Seite zählt, EXIF-Drehung, flaues/unscharfes/einfarbiges Bild (Warnungen), Schärfe unabhängig von der Bildgröße, transparentes PNG, kaputte Datei mit richtigem Anfang, „Dekompressionsbombe“, Produkt ohne Gravurbereich.

## Bekannte Grenzen

- **Kein Hochskalieren:** Bilder mit Faktor über 1 werden nur markiert. Hochskaliert wird erst in US06.
- **Grenzwerte nur mit Testbildern geprüft:** 5 Beispielfotos mit künstlicher Unschärfe. Mit echten Handyfotos nachjustieren (Konstanten oben in `quality.py`).
- **`product_type` wird nicht geprüft:** entscheidend ist nur, ob ein Gravurbereich eingetragen ist.
- **Keine Oberfläche:** Es gibt noch keinen Upload-Knopf im Frontend (US04 Task 4).
- **Produkt-IDs:** Der Upload braucht ein Produkt in der Datenbank. Solange die Katalog-API fehlt, kennt das Frontend nur fest eingetragene Produkte.
- **Alte Uploads werden nicht aufgeräumt:** Lädt ein Kunde mehrmals hoch, bleiben alle Bilder gespeichert.

## So erweiterst du das Modul

- **Neuen Dateityp zulassen:** in `detect_image_type()` die ersten Bytes des Formats ergänzen, `MSG_TYPE` anpassen, Test in `tests/test_images_service.py` (`test_png_and_jpeg_are_accepted`) ergänzen und den Fall aus `test_wrong_type_is_rejected` entfernen.
- **Größengrenze ändern:** `MAX_BYTES` in `app/images/service.py` ändern. Die Meldung `MSG_SIZE` und die Router-Vorabprüfung passen sich automatisch an.
- **Grenzwert ändern:** Konstante oben in `app/images/quality.py` (`PIXELS_PER_MM`, `MARGIN_MM`, `MAX_UPSCALE_FACTOR`, `MIN_CONTRAST`, `MIN_SHARPNESS`), dann `tests/test_images_quality.py` laufen lassen. Die Meldungen passen sich an.
- **Neue Warnung hinzufügen:** Messfunktion in `quality.py`, in `check_quality()` aufrufen und Text in `warnings` anhängen. Sie landet automatisch in `quality_warning` und in der API-Antwort.
