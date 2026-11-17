"""Tests für den Bildspeicher (app/storage.py).

Lokal: Dateien landen in einem temporären Ordner (tmp_path), nie im echten uploads/.
Object Storage: ein botocore-Stubber antwortet anstelle des Servers. Es wird keine
Netzwerkverbindung aufgebaut.
"""

import io

import boto3
import pytest
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from botocore.stub import Stubber

from app import config, storage

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
BUCKET = "testbucket"


@pytest.fixture(autouse=True)
def local_storage(tmp_path, monkeypatch):
    """Jeder Test startet im lokalen Modus mit leerem Ordner und ohne gemerkten Client."""
    monkeypatch.setattr(config, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(config, "STORAGE_BUCKET", "")
    storage.set_client(None)
    yield tmp_path
    storage.set_client(None)


@pytest.fixture
def s3():
    """Ein echter boto3-Client, dessen Antworten ein Stubber vorgibt (ohne Netz)."""
    client = boto3.client(
        "s3",
        region_name="eu-central-1",
        endpoint_url="https://example.invalid",
        aws_access_key_id="x",
        aws_secret_access_key="y",
    )
    stubber = Stubber(client)
    storage.set_client(client)
    with stubber:
        yield stubber
        stubber.assert_no_pending_responses()


@pytest.fixture
def bucket(monkeypatch):
    """Schaltet auf den Object Storage um (per Monkeypatch, nie mit echter .env)."""
    monkeypatch.setattr(config, "STORAGE_BUCKET", BUCKET)


# ------------------------------------------------------------------ Auswahl des Ablageorts


def test_use_object_storage_follows_config_at_runtime(monkeypatch):
    assert storage.use_object_storage() is False
    monkeypatch.setattr(config, "STORAGE_BUCKET", BUCKET)
    assert storage.use_object_storage() is True


# ------------------------------------------------------------------ Lokal


def test_local_save_read_delete(local_storage):
    storage.save_file("avatars/1-ab.png", PNG)
    assert (local_storage / "avatars" / "1-ab.png").read_bytes() == PNG  # Unterordner wird angelegt
    assert storage.read_file("avatars/1-ab.png") == PNG

    storage.delete_file("avatars/1-ab.png")
    assert not (local_storage / "avatars" / "1-ab.png").exists()
    assert storage.read_file("avatars/1-ab.png") is None


def test_local_save_overwrites_existing_file():
    storage.save_file("avatars/1-ab.png", PNG)
    storage.save_file("avatars/1-ab.png", b"neu")
    assert storage.read_file("avatars/1-ab.png") == b"neu"


def test_local_read_unknown_returns_none():
    assert storage.read_file("avatars/gibt-es-nicht.png") is None


@pytest.mark.parametrize("key", [None, "", "avatars/gibt-es-nicht.png"])
def test_local_delete_unknown_or_empty_does_nothing(key):
    storage.delete_file(key)  # darf keinen Fehler werfen


@pytest.mark.parametrize("key", ["../x.png", "/x.png", "a\\b.png", "C:x.png", "", "avatars/../x.png"])
def test_save_rejects_invalid_keys(key, local_storage):
    with pytest.raises(ValueError):
        storage.save_file(key, PNG)
    assert list(local_storage.iterdir()) == []  # nichts geschrieben


@pytest.mark.parametrize("key", ["uploads/../x", "C:\\x.png", "/x.png", "a\\b.png"])
def test_read_and_delete_ignore_invalid_keys(key, local_storage):
    """Alte Werte aus der Zeit vor dem Bildspeicher dürfen die App nicht zum Absturz bringen."""
    (local_storage / "x").write_bytes(b"datei")  # die Datei, auf die "uploads/../x" zeigen würde
    (local_storage / "x.png").write_bytes(b"datei")
    assert storage.read_file(key) is None
    storage.delete_file(key)
    assert (local_storage / "x").read_bytes() == b"datei"  # nichts gelöscht
    assert (local_storage / "x.png").read_bytes() == b"datei"


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("a.jpg", "image/jpeg"),
        ("a.jpeg", "image/jpeg"),
        ("a.png", "image/png"),
        ("a.webp", "image/webp"),
        ("a.svg", "image/svg+xml"),
        ("a.dxf", "application/dxf"),
        ("avatars/3-abc.PNG", "image/png"),  # Groß- und Kleinschreibung egal
        ("a.txt", "application/octet-stream"),
        ("ohne-endung", "application/octet-stream"),
    ],
)
def test_content_type_for(key, expected):
    assert storage.content_type_for(key) == expected


# ------------------------------------------------------------------ Object Storage (Stubber)


def test_object_storage_save_sends_expected_request(s3, bucket):
    s3.add_response(
        "put_object",
        {},
        expected_params={"Bucket": BUCKET, "Key": "avatars/1-ab.png", "Body": PNG, "ContentType": "image/png"},
    )
    storage.save_file("avatars/1-ab.png", PNG)


def test_object_storage_save_uses_given_content_type(s3, bucket):
    s3.add_response(
        "put_object",
        {},
        expected_params={"Bucket": BUCKET, "Key": "x.bin", "Body": b"abc", "ContentType": "text/plain"},
    )
    storage.save_file("x.bin", b"abc", content_type="text/plain")


def test_object_storage_read_returns_content(s3, bucket):
    s3.add_response(
        "get_object",
        {"Body": StreamingBody(io.BytesIO(PNG), len(PNG))},
        expected_params={"Bucket": BUCKET, "Key": "avatars/1-ab.png"},
    )
    assert storage.read_file("avatars/1-ab.png") == PNG


@pytest.mark.parametrize("code", ["NoSuchKey", "404", "NotFound"])
def test_object_storage_read_missing_returns_none(s3, bucket, code):
    s3.add_client_error(
        "get_object",
        service_error_code=code,
        http_status_code=404,
        expected_params={"Bucket": BUCKET, "Key": "avatars/fehlt.png"},
    )
    assert storage.read_file("avatars/fehlt.png") is None


def test_object_storage_read_other_error_is_raised(s3, bucket):
    s3.add_client_error(
        "get_object",
        service_error_code="AccessDenied",
        http_status_code=403,
        expected_params={"Bucket": BUCKET, "Key": "avatars/1-ab.png"},
    )
    with pytest.raises(ClientError):
        storage.read_file("avatars/1-ab.png")


def test_object_storage_invalid_key_sends_no_request(s3, bucket):
    """Ungültige Schlüssel gehen gar nicht erst an den Server (der Stubber hätte sonst gemeckert)."""
    assert storage.read_file("uploads/../x") is None
    storage.delete_file("/x.png")
    with pytest.raises(ValueError):
        storage.save_file("../x.png", PNG)


def test_object_storage_delete_sends_expected_request(s3, bucket):
    s3.add_response("delete_object", {}, expected_params={"Bucket": BUCKET, "Key": "avatars/1-ab.png"})
    storage.delete_file("avatars/1-ab.png")


def test_object_storage_delete_none_sends_no_request(s3, bucket):
    storage.delete_file(None)
    storage.delete_file("")


def test_client_is_created_once_and_cached(monkeypatch):
    monkeypatch.setattr(config, "STORAGE_ENDPOINT_URL", "https://example.invalid")
    monkeypatch.setattr(config, "STORAGE_REGION", "eu-central-1")
    monkeypatch.setattr(config, "STORAGE_ACCESS_KEY_ID", "x")
    monkeypatch.setattr(config, "STORAGE_SECRET_ACCESS_KEY", "y")
    first = storage._get_client()  # baut nur den Client, es wird keine Verbindung aufgebaut
    assert storage._get_client() is first


def test_missing_settings_raise_runtime_error_without_secret_values(monkeypatch):
    monkeypatch.setattr(config, "STORAGE_BUCKET", BUCKET)
    monkeypatch.setattr(config, "STORAGE_ENDPOINT_URL", "")
    monkeypatch.setattr(config, "STORAGE_ACCESS_KEY_ID", "")
    monkeypatch.setattr(config, "STORAGE_SECRET_ACCESS_KEY", "geheimwert-123")

    with pytest.raises(RuntimeError) as error:
        storage.save_file("avatars/1-ab.png", PNG)

    message = str(error.value)
    assert "AWS_ENDPOINT_URL_S3" in message
    assert "AWS_ACCESS_KEY_ID" in message
    assert "AWS_SECRET_ACCESS_KEY" not in message  # dieser Wert ist gesetzt, fehlt also nicht
    assert "geheimwert-123" not in message
