# Modul: Bildspeicher (Neon Object Storage oder lokal)

> Bereich: Grundlage für Dateien (Profilbilder, US10; Kundenbilder, US04; später Produktbilder)
> Stand: 24.11.2026. Profilbilder und Kundenbilder liegen im Bildspeicher. Produktbilder nutzen ihn noch nicht.
> Hinweis: Eine gemeinsame Vorlage `docs/module/_vorlage.md` gibt es noch nicht. Diese Datei folgt dem Aufbau von `docs/module/datenbank.md`.

## Zweck

Die Datenbank ist im Team gemeinsam (Neon). Die Bilddateien lagen aber nur im Ordner `uploads/` auf dem eigenen Rechner. Andere Teammitglieder sahen deshalb keine Profilbilder der anderen.

Der Baustein `app/storage.py` legt Dateien an einem von zwei Orten ab:

- **Neon Object Storage** (Cloud, S3-kompatibel, Zugriff über `boto3`). Aktiv, sobald `STORAGE_BUCKET` in der `.env` gesetzt ist.
- **Lokal** im Ordner `UPLOAD_DIR` (Standard `./uploads`). Ohne Bucket. Nur auf dem eigenen Rechner sichtbar.

In der Datenbank steht nur der **Schlüssel** der Datei, z. B. `avatars/3-a1b2c3d4e5f6a7b8.png`. Die Tabellen ändern sich dafür nicht.

## Dateien

| Datei | Aufgabe |
| --- | --- |
| `app/storage.py` | Der Baustein: `save_file`, `read_file`, `delete_file`, `content_type_for`, `use_object_storage`. Baut den boto3-Client beim ersten Zugriff (`_get_client`) |
| `app/config.py` | Block „Bildspeicher“: liest die `STORAGE_*`-Werte aus der `.env` |
| `app/accounts/account_service.py` | Speichert, liest und löscht Profilbilder über den Baustein (`save_avatar`, `avatar_image`, `remove_avatar`) |
| `app/accounts/account_router.py` | `GET /api/account/avatar` liefert Inhalt und Content-Type aus dem Baustein |
| `.env.example` | Vorlage mit den Variablen des Bildspeichers (ohne echte Schlüssel) |
| `requirements.txt` | Enthält `boto3>=1.34` |
| `tests/test_storage.py` | Tests lokal und mit Stubber (kein Netz) |
| `tests/conftest.py` | Setzt `STORAGE_BUCKET` für Tests auf leer |

## Einstellungen

Alle Werte kommen aus der `.env`. Die Namen `AWS_*` sind die, die Neon in der Console unter „Connect“, Reiter „Storage“, „Parameters only“ anzeigt.

| Variable | Bedeutung |
| --- | --- |
| `STORAGE_BUCKET` | Name des Buckets, z. B. `laserflow-bilder`. Leer = lokaler Ordner `UPLOAD_DIR` |
| `AWS_ENDPOINT_URL_S3` | Adresse des Speichers, z. B. `https://BRANCH-ID.storage.REGION.aws.neon.tech` |
| `AWS_REGION` | Region, z. B. `eu-central-1` |
| `AWS_ACCESS_KEY_ID` | Schlüssel-ID |
| `AWS_SECRET_ACCESS_KEY` | Geheimer Schlüssel. Nur in der eigenen `.env`, nie in Git oder im Chat |

Fehlt `AWS_ENDPOINT_URL_S3`, `AWS_ACCESS_KEY_ID` oder `AWS_SECRET_ACCESS_KEY`, wirft der Baustein einen `RuntimeError`. Die Meldung nennt die fehlenden Variablen, aber nie deren Werte.

## Benutzung im Code

Der Schlüssel ist ein relativer Pfad mit `/` als Trenner, z. B. `avatars/<user-id>-<zufall>.<endung>`. Ungültig sind ein führendes `/`, ein `\`, ein `:` und ein `..`-Teil.

```python
from app import storage

storage.save_file("avatars/3-a1b2c3d4e5f6a7b8.png", inhalt)  # ValueError bei ungültigem Schlüssel
bild = storage.read_file("avatars/3-a1b2c3d4e5f6a7b8.png")  # None, wenn es die Datei nicht gibt
storage.delete_file("avatars/3-a1b2c3d4e5f6a7b8.png")       # tut nichts, wenn es sie nicht gibt
typ = storage.content_type_for("avatars/3-a1b2c3d4e5f6a7b8.png")  # "image/png"
```

Für einen neuen Dateityp muss nur `_CONTENT_TYPES` in `app/storage.py` ergänzt werden.

## Bewusste Entscheidungen

- **Nur der Schlüssel in der Datenbank:** Der Ablageort (Bucket oder lokal) kann sich ändern, ohne dass Daten umgeschrieben werden müssen.
- **Fallback lokal ohne Bucket:** Ohne Internet oder ohne Zugangsdaten läuft die App wie bisher mit `uploads/`.
- **Zur Laufzeit gelesen:** `use_object_storage()` liest `config.STORAGE_BUCKET` bei jedem Aufruf. So können Tests zwischen Bucket und lokal umschalten.
- **Tests nie gegen Neon:** `tests/conftest.py` setzt `STORAGE_BUCKET` auf leer, bevor die App geladen wird. Die Object-Storage-Tests nutzen einen Stubber, der keine Verbindung aufbaut.
- **Ungültige alte Pfade still ignoriert:** Lesen liefert `None`, Löschen tut nichts. Alte Werte wie `uploads/avatars/x.png` oder absolute Pfade sollen die App nicht zum Absturz bringen.
- **Einstellungen für Neon im boto3-Client:** Neon versteht nur „path-style“-Adressen (`<endpunkt>/<bucket>/<key>`), deshalb `addressing_style: path`. Prüfsummen schickt boto3 nur, wo sie Pflicht sind, weil neuere boto3-Versionen sie sonst immer anhängen und S3-kompatible Speicher das oft ablehnen. Der Schlüssel gilt nur für den Neon-Branch, auf dem er erzeugt wurde (bei uns `production`).
- **boto3 statt eigenem HTTP:** Der S3-Zugriff ist Standard und in boto3 gut getestet. Die Retries (bis 5 Versuche) fängt boto3 selbst ab.
- **Kundenbilder im Bildspeicher (seit 24.11.2026, US04):** Der Upload speichert sie unter `customer-images/<user_id>-<zufall>.<jpg|png>` (siehe `bild-upload.md`). Beim Anonymisieren (US10) löscht `account_service._anonymize` sie ebenfalls über `delete_file`, lokal und im Bucket. Die frühere Sonderfunktion `_delete_local_file` gibt es nicht mehr.

## Testen

- Nur der Baustein: `pytest tests/test_storage.py`.
- Konto-Tests mit Profilbild: `pytest tests/test_account.py tests/test_account_router.py`.
- Der volle Lauf: `pytest`.

## Bekannte Grenzen

- **Alte Profilbilder werden nicht übertragen:** Bilder, die vor dieser Umstellung lokal in `uploads/avatars/` lagen, sind im Object Storage nicht vorhanden. Der Kunde lädt sein Profilbild einfach neu hoch. Der alte lokale Eintrag liefert bis dahin kein Bild (404) und wird beim Ersetzen nicht mehr von der Platte gelöscht.
- **Bild läuft über unseren Server:** Die App liefert das Bild selbst aus (`GET /api/account/avatar`). Der Browser lädt es nicht direkt aus Neon.
- **Produktbilder nutzen den Baustein noch nicht.**
- **Neon Object Storage ist neu.** Laut Neon-Doku (Stand 11.2026) gilt im Free Plan ein Limit von 5 GB pro Projekt. Bei hoher Last antwortet der Speicher mit `503 SlowDown`. boto3 wiederholt die Anfrage, bei anhaltender Überlast schlägt der Upload trotzdem fehl.
- **Lokale Dateien und Bucket sind getrennt:** Wer ohne Bucket arbeitet, sieht die Profilbilder der anderen nicht.
