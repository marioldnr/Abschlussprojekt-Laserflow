"""E-Mail-Versand für LaserFlow (gemeinsamer Baustein für alle Module).

Je nach ``config.MAIL_MODE``:
    "smtp":    Die E-Mail geht wirklich raus, über das Gmail-Konto des Teams
               (smtp.gmail.com, Port 587, verschlüsselt mit STARTTLS, Anmeldung mit App-Passwort).
               Adresse und App-Passwort stehen in der lokalen .env (siehe .env.example).
    "console": Die E-Mail wird nur im Terminal ausgegeben, in dem uvicorn läuft.
               Das ist der Standard, solange keine .env mit Zugangsdaten da ist.

Schlägt der echte Versand fehl (kein Internet, falsches Passwort ...), wird die E-Mail
zusätzlich im Terminal ausgegeben. So bricht z. B. die Registrierung nicht ab, und beim
Entwickeln kann man den Code trotzdem ablesen.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app import config

logger = logging.getLogger(__name__)


def send_mail(to: str, subject: str, body: str) -> bool:
    """Verschickt eine einfache Text-E-Mail.

    Args:
        to: Empfängeradresse.
        subject: Betreff.
        body: Text der E-Mail (ohne HTML).

    Returns:
        True, wenn die E-Mail wirklich verschickt wurde. False, wenn sie nur im Terminal
        steht (Modus "console" oder Versand fehlgeschlagen).
    """
    if config.MAIL_MODE == "smtp":
        try:
            _send_smtp(to, subject, body)
            return True
        except OSError as error:
            # smtplib.SMTPException (z. B. falsches Passwort) ist eine Unterklasse von OSError,
            # genau wie Netzwerkfehler. Das Passwort steht nie in der Meldung.
            logger.warning("E-Mail an %s konnte nicht verschickt werden: %s", to, error)
            _print_to_console(to, subject, body, note=f"VERSAND FEHLGESCHLAGEN: {error}")
            return False

    _print_to_console(to, subject, body, note="nur im Terminal, keine Zugangsdaten in der .env")
    return False


# Port für "SMTP über SSL": Verbindung ist von Anfang an verschlüsselt (statt STARTTLS auf 587).
SMTP_SSL_PORT = 465


def _send_smtp(to: str, subject: str, body: str) -> None:
    """Verschickt die E-Mail über den SMTP-Server aus config (Gmail).

    Erst über den eingestellten Port (Standard 587 mit STARTTLS). Manche Netze (Schul-WLAN,
    Virenscanner, Firewall) kappen Port 587; dann wird einmal Port 465 (SSL) versucht.
    Bei falschem Passwort wird nicht noch einmal versucht, das würde nichts ändern.

    Raises:
        OSError: Server nicht erreichbar, Anmeldung oder Versand fehlgeschlagen.
            Die Meldung nennt den Schritt, bei dem es scheiterte.
    """
    message = EmailMessage()
    message["From"] = config.MAIL_SENDER
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        _deliver(message, config.SMTP_PORT)
    except smtplib.SMTPAuthenticationError:
        raise
    except OSError as error:
        if config.SMTP_PORT == SMTP_SSL_PORT:
            raise
        logger.warning("Versand über Port %s gescheitert (%s), versuche Port %s.", config.SMTP_PORT, error, SMTP_SSL_PORT)
        _deliver(message, SMTP_SSL_PORT)


def _deliver(message: EmailMessage, port: int) -> None:
    """Ein Versandversuch über einen Port: verbinden → verschlüsseln → anmelden → senden.

    ``ssl.create_default_context()`` prüft das Zertifikat des Servers.
    Scheitert ein Schritt, steht sein Name in der Fehlermeldung (hilft bei der Fehlersuche).
    """
    context = ssl.create_default_context()
    step = f"Verbinden mit {config.SMTP_HOST}:{port}"
    try:
        if port == SMTP_SSL_PORT:
            server = smtplib.SMTP_SSL(config.SMTP_HOST, port, timeout=config.SMTP_TIMEOUT_SECONDS, context=context)
        else:
            server = smtplib.SMTP(config.SMTP_HOST, port, timeout=config.SMTP_TIMEOUT_SECONDS)
        with server:
            if port != SMTP_SSL_PORT:
                step = "Verschlüsselung (STARTTLS)"
                server.starttls(context=context)
            if config.SMTP_USER:
                step = "Anmeldung"
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            step = "Senden"
            server.send_message(message)
    except smtplib.SMTPAuthenticationError:
        raise
    except OSError as error:
        raise OSError(f"Schritt '{step}': {error}") from error


def _print_to_console(to: str, subject: str, body: str, note: str) -> None:
    """Gibt die E-Mail gut sichtbar im Terminal aus."""
    print(
        "\n" + "=" * 60
        + f"\nE-MAIL ({note})\nAn:      {to}\nBetreff: {subject}\n"
        + "-" * 60 + f"\n{body}\n" + "=" * 60 + "\n",
        flush=True,
    )
