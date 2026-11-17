"""Bildspeicher: Dateien (Profilbilder, später Produktbilder) ablegen, lesen und löschen.

Es gibt zwei Ablageorte:

- **Neon Object Storage** (Cloud, S3-kompatibel, Zugriff über boto3). Aktiv, sobald
  ``STORAGE_BUCKET`` in der ``.env`` gesetzt ist.
- **Lokal** im Ordner ``config.UPLOAD_DIR`` (Standard ``./uploads``). Ohne Bucket.

Warum: Die Datenbank ist im Team gemeinsam (Neon), die Dateien lagen aber nur auf dem
eigenen Rechner. Andere Teammitglieder sahen so keine Profilbilder. Im Object Storage
liegen die Dateien dort, wo auch alle anderen zugreifen können.

In der Datenbank steht nur der Schlüssel ("key") der Datei, z. B.
``avatars/3-a1b2c3d4e5f6a7b8.png``. Der Schlüssel ist ein relativer Pfad mit "/" als
Trenner, ohne führendes "/", ohne "\\", ohne ":" und ohne ".."-Teile. So ist der Schlüssel
auf beiden Ablageorten gleich und lässt sich nicht aus dem Ordner herauslösen.

Tests laufen immer lokal: ``tests/conftest.py`` setzt ``STORAGE_BUCKET`` auf leer, damit
nie der echte Bildspeicher berührt wird, auch wenn die eigene ``.env`` einen Bucket nennt.
Die Object-Storage-Tests nutzen einen Stubber von botocore, der keine Netzwerkverbindung aufbaut.
"""

from pathlib import Path

import boto3
import botocore.config
from botocore.exceptions import ClientError

from app import config

# Fehlercodes, mit denen S3 meldet, dass ein Objekt nicht existiert.
_NOT_FOUND_CODES = {"NoSuchKey", "404", "NotFound"}

# Endung -> Content-Type für die Auslieferung im Browser.
_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".dxf": "application/dxf",
}

# Der boto3-Client wird beim ersten Zugriff angelegt und hier gemerkt (siehe _get_client).
_client = None


def use_object_storage() -> bool:
    """Prüft, ob der Neon Object Storage genutzt wird.

    Die Einstellung wird bei jedem Aufruf aus ``config`` gelesen und nicht beim Import
    kopiert. So können Tests mit monkeypatch zwischen Bucket und lokal umschalten.

    Returns:
        True, wenn ``config.STORAGE_BUCKET`` nicht leer ist, sonst False (lokal).
    """
    return bool(config.STORAGE_BUCKET)


def set_client(client) -> None:
    """Setzt den boto3-Client (nur für Tests) oder setzt ihn mit None zurück.

    Args:
        client: ein boto3-S3-Client, z. B. mit botocore-Stubber in den Tests. None löscht
            den gemerkten Client, damit er beim nächsten Zugriff neu angelegt wird.
    """
    global _client
    _client = client


def content_type_for(key: str) -> str:
    """Liefert den Content-Type aus der Endung des Schlüssels.

    Args:
        key: der Schlüssel oder Dateiname, z. B. ``avatars/3-abc.png``.

    Returns:
        z. B. ``image/png``. Groß- und Kleinschreibung der Endung spielen keine Rolle.
        Unbekannte Endungen ergeben ``application/octet-stream``.
    """
    return _CONTENT_TYPES.get(Path(key).suffix.lower(), "application/octet-stream")


def _check_key(key: str) -> bool:
    """Prüft, ob ein Schlüssel gültig ist.

    Gültig ist ein nicht leerer, relativer Pfad mit "/" als Trenner, ohne "\\", ohne ":"
    und ohne ".."-Teil. Das schützt vor Pfaden, die aus dem Ordner ausbrechen.

    Returns:
        True, wenn der Schlüssel gültig ist, sonst False.
    """
    if not key or key.startswith("/") or "\\" in key or ":" in key:
        return False
    return ".." not in key.split("/")


def _local_path(key: str) -> Path:
    """Pfad der Datei im lokalen Ordner (``config.UPLOAD_DIR``)."""
    return Path(config.UPLOAD_DIR) / key


def _get_client():
    """Liefert den boto3-Client für den Neon Object Storage und merkt ihn sich.

    Der Client wird erst beim ersten Zugriff gebaut. Die Schlüssel stehen in der ``.env``.
    Die Fehlermeldung nennt nur die Namen der fehlenden Variablen, nie deren Werte.

    Raises:
        RuntimeError: Endpunkt, Schlüssel-ID oder geheimer Schlüssel fehlen in der ``.env``.
    """
    global _client
    if _client is not None:
        return _client

    missing = [
        name
        for name, value in (
            ("AWS_ENDPOINT_URL_S3", config.STORAGE_ENDPOINT_URL),
            ("AWS_ACCESS_KEY_ID", config.STORAGE_ACCESS_KEY_ID),
            ("AWS_SECRET_ACCESS_KEY", config.STORAGE_SECRET_ACCESS_KEY),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Der Bildspeicher ist nicht vollständig eingerichtet. "
            f"In der .env fehlen: {', '.join(missing)}."
        )

    _client = boto3.client(
        "s3",
        endpoint_url=config.STORAGE_ENDPOINT_URL,
        region_name=config.STORAGE_REGION or None,
        aws_access_key_id=config.STORAGE_ACCESS_KEY_ID,
        aws_secret_access_key=config.STORAGE_SECRET_ACCESS_KEY,
        config=botocore.config.Config(
            # Neon kann bei viel Last mit "503 SlowDown" bremsen. boto3 wiederholt die Anfrage
            # dann automatisch, bis zu 5 Versuche mit wachsender Pause.
            retries={"max_attempts": 5, "mode": "standard"},
            # Neon versteht nur Adressen der Form <endpunkt>/<bucket>/<key> ("path-style"),
            # nicht <bucket>.<endpunkt>/<key>. Ohne diese Zeile könnte boto3 die zweite Form wählen.
            s3={"addressing_style": "path"},
            # Neuere boto3-Versionen hängen von sich aus Prüfsummen an jede Anfrage an. Viele
            # S3-kompatible Speicher kennen das nicht. Prüfsummen deshalb nur, wo sie Pflicht sind.
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )
    return _client


def save_file(key: str, content: bytes, content_type: str | None = None) -> None:
    """Speichert eine Datei unter dem Schlüssel. Eine vorhandene Datei wird überschrieben.

    Args:
        key: relativer Pfad, z. B. ``avatars/3-abc.png``.
        content: der Inhalt der Datei als Bytes.
        content_type: optionaler Content-Type. Ohne Angabe wird er aus der Endung ermittelt
            (siehe content_type_for).

    Raises:
        ValueError: der Schlüssel ist ungültig (siehe _check_key).
        RuntimeError: der Object Storage ist nicht eingerichtet (siehe _get_client).
        botocore.exceptions.ClientError: der Object Storage meldet einen Fehler.
    """
    if not _check_key(key):
        raise ValueError(f"Ungültiger Schlüssel für eine Datei: {key!r}")

    if use_object_storage():
        _get_client().put_object(
            Bucket=config.STORAGE_BUCKET,
            Key=key,
            Body=content,
            ContentType=content_type or content_type_for(key),
        )
        return

    path = _local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def read_file(key: str) -> bytes | None:
    """Liest eine Datei.

    Ein ungültiger Schlüssel wird NICHT als Fehler behandelt, sondern ergibt None. Grund:
    Alte Werte aus der Zeit vor dieser Umstellung (z. B. ``uploads/avatars/x.png`` oder
    Windows-Pfade) sollen die App nicht zum Absturz bringen. Sie zeigen dann einfach kein Bild.

    Args:
        key: relativer Pfad, z. B. ``avatars/3-abc.png``.

    Returns:
        der Inhalt als Bytes, oder None, wenn es die Datei nicht gibt.

    Raises:
        RuntimeError: der Object Storage ist nicht eingerichtet (siehe _get_client).
        botocore.exceptions.ClientError: anderer Fehler als "nicht gefunden", z. B. 403.
    """
    if not _check_key(key):
        return None

    if use_object_storage():
        try:
            response = _get_client().get_object(Bucket=config.STORAGE_BUCKET, Key=key)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in _NOT_FOUND_CODES:
                return None
            raise
        return response["Body"].read()

    path = _local_path(key)
    if not path.is_file():
        return None
    return path.read_bytes()


def delete_file(key: str | None) -> None:
    """Löscht eine Datei. Tut nichts, wenn es sie nicht gibt.

    Ein leerer oder ungültiger Schlüssel (z. B. ein alter lokaler Pfad) wird ignoriert,
    aus demselben Grund wie bei read_file. Der Object Storage meldet beim Löschen eines
    fehlenden Objekts keinen Fehler.

    Args:
        key: relativer Pfad, oder None.

    Raises:
        RuntimeError: der Object Storage ist nicht eingerichtet (siehe _get_client).
        botocore.exceptions.ClientError: der Object Storage meldet einen Fehler.
    """
    if not key or not _check_key(key):
        return

    if use_object_storage():
        _get_client().delete_object(Bucket=config.STORAGE_BUCKET, Key=key)
        return

    _local_path(key).unlink(missing_ok=True)
