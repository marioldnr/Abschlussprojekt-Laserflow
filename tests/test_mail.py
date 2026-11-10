"""Tests für den E-Mail-Versand (app/mail.py) und das Lesen der .env (app/config.py).

Es wird nie wirklich verschickt: smtplib.SMTP wird durch eine Attrappe ersetzt,
die sich merkt, was passiert wäre.
"""

import os
import smtplib

import pytest

from app import config, mail


class FakeSMTP:
    """Attrappe für smtplib.SMTP. Merkt sich Verbindung, Anmeldung und verschickte Nachrichten."""

    instances = []
    fail_with = None  # Ausnahme, die beim Senden geworfen werden soll
    blocked_ports = ()  # Ports, auf denen die Verbindung sofort abbricht (z. B. Firewall)

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.timeout = host, port, timeout
        if port in FakeSMTP.blocked_ports:
            FakeSMTP.instances.append(self)
            raise smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
        self.started_tls = False
        self.login_data = None
        self.sent = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self, context=None):
        self.started_tls = True

    def login(self, user, password):
        self.login_data = (user, password)

    def send_message(self, message):
        if FakeSMTP.fail_with:
            raise FakeSMTP.fail_with
        self.sent.append(message)


@pytest.fixture
def fake_smtp(monkeypatch):
    """Ersetzt smtplib.SMTP und stellt auf echten Versand mit Test-Zugangsdaten."""
    FakeSMTP.instances = []
    FakeSMTP.fail_with = None
    FakeSMTP.blocked_ports = ()
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    monkeypatch.setattr(config, "MAIL_MODE", "smtp")
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(config, "SMTP_PORT", 587)
    monkeypatch.setattr(config, "SMTP_USER", "team@gmail.com")
    monkeypatch.setattr(config, "SMTP_PASSWORD", "abcdabcdabcdabcd")
    monkeypatch.setattr(config, "MAIL_SENDER", "LaserFlow <team@gmail.com>")
    return FakeSMTP


# ------------------------------------------------------------------ Versand


def test_smtp_sends_encrypted_with_login(fake_smtp):
    assert mail.send_mail("kunde@example.de", "Betreff", "Hallo") is True

    server = fake_smtp.instances[0]
    assert (server.host, server.port) == ("smtp.gmail.com", 587)
    assert server.timeout == config.SMTP_TIMEOUT_SECONDS
    assert server.started_tls is True  # verschlüsselt, bevor das Passwort geschickt wird
    assert server.login_data == ("team@gmail.com", "abcdabcdabcdabcd")
    message = server.sent[0]
    assert message["To"] == "kunde@example.de"
    assert message["From"] == "LaserFlow <team@gmail.com>"
    assert message["Subject"] == "Betreff"
    assert "Hallo" in message.get_content()


@pytest.mark.parametrize(
    "error",
    [
        smtplib.SMTPAuthenticationError(535, b"Username and Password not accepted"),  # falsches App-Passwort
        ConnectionRefusedError("kein Server"),  # kein Internet / Server nicht erreichbar
        TimeoutError("zu langsam"),
    ],
)
def test_smtp_failure_falls_back_to_console(fake_smtp, capsys, error):
    fake_smtp.fail_with = error

    assert mail.send_mail("kunde@example.de", "Dein Code", "Code: 1234") is False

    output = capsys.readouterr().out
    assert "VERSAND FEHLGESCHLAGEN" in output
    assert "Code: 1234" in output  # Code bleibt ablesbar
    assert "abcdabcdabcdabcd" not in output  # Passwort taucht nie auf


def test_blocked_port_587_falls_back_to_ssl_port_465(fake_smtp):
    """Netz kappt Port 587 (wie bei Sita am 10.11.2026): zweiter Versuch über 465 klappt."""
    fake_smtp.blocked_ports = (587,)

    assert mail.send_mail("kunde@example.de", "Betreff", "Hallo") is True

    first, second = fake_smtp.instances
    assert (first.port, second.port) == (587, 465)
    assert second.started_tls is False  # 465 ist schon verschlüsselt, kein STARTTLS
    assert second.login_data == ("team@gmail.com", "abcdabcdabcdabcd")
    assert len(second.sent) == 1


def test_both_ports_blocked_names_the_step(fake_smtp, capsys):
    fake_smtp.blocked_ports = (587, 465)
    assert mail.send_mail("kunde@example.de", "Dein Code", "Code: 1234") is False
    assert "Code: 1234" in capsys.readouterr().out
    assert [server.port for server in fake_smtp.instances] == [587, 465]


def test_wrong_password_is_not_retried(fake_smtp):
    fake_smtp.fail_with = smtplib.SMTPAuthenticationError(535, b"not accepted")
    assert mail.send_mail("kunde@example.de", "Betreff", "Hallo") is False
    assert len(fake_smtp.instances) == 1  # kein zweiter Versuch


def test_console_mode_prints_and_sends_nothing(monkeypatch, capsys):
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: pytest.fail("darf nicht verbinden"))
    # MAIL_MODE ist durch die Fixture in conftest.py schon "console"
    assert mail.send_mail("kunde@example.de", "Dein Code", "Code: 4711") is False
    output = capsys.readouterr().out
    assert "kunde@example.de" in output
    assert "Code: 4711" in output


# ------------------------------------------------------------------ Einstellungen


def test_default_mail_mode():
    assert config.default_mail_mode("team@gmail.com", "geheim") == "smtp"
    assert config.default_mail_mode("team@gmail.com", "") == "console"
    assert config.default_mail_mode("", "geheim") == "console"
    assert config.default_mail_mode("", "") == "console"


def test_load_env_file(tmp_path, monkeypatch):
    for name in ("LF_TEST_A", "LF_TEST_B", "LF_TEST_C", "LF_TEST_LEER", "LF_TEST_SCHON_DA"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LF_TEST_SCHON_DA", "von außen")
    env = tmp_path / ".env"
    env.write_text(
        "# Kommentar\n"
        "\n"
        "LF_TEST_A=einfach\n"
        'LF_TEST_B = "mit Anführungszeichen"\n'
        "LF_TEST_C=abcd efgh=ijkl\n"  # Gleichheitszeichen im Wert bleibt erhalten
        "LF_TEST_LEER=\n"
        "ZEILE OHNE GLEICHHEITSZEICHEN\n"
        "LF_TEST_SCHON_DA=aus der Datei\n",
        encoding="utf-8",
    )

    config.load_env_file(env)

    assert os.environ["LF_TEST_A"] == "einfach"
    assert os.environ["LF_TEST_B"] == "mit Anführungszeichen"
    assert os.environ["LF_TEST_C"] == "abcd efgh=ijkl"
    assert os.environ["LF_TEST_LEER"] == ""
    assert os.environ["LF_TEST_SCHON_DA"] == "von außen"  # vorhandene Variable gewinnt


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16"])
def test_load_env_file_from_windows_editors(tmp_path, monkeypatch, encoding):
    """Notepad/PowerShell speichern mit BOM bzw. als UTF-16; die erste Zeile muss trotzdem stimmen."""
    monkeypatch.delenv("LF_TEST_ERSTE", raising=False)
    env = tmp_path / ".env"
    env.write_text("LF_TEST_ERSTE=wert\n", encoding=encoding)
    config.load_env_file(env)
    assert os.environ["LF_TEST_ERSTE"] == "wert"


def test_load_env_file_missing_file_does_nothing(tmp_path):
    config.load_env_file(tmp_path / "gibt-es-nicht.env")  # kein Fehler
