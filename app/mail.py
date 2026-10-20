"""E-Mail-Versand für LaserFlow (gemeinsamer Baustein für alle Module).

Laut Projektvorgaben gibt es keinen Cloud-Dienst. Je nach ``config.MAIL_MODE``:
    "console": Die E-Mail wird nur im Terminal ausgegeben, in dem uvicorn läuft.
               Praktisch beim Entwickeln: Den Bestätigungscode liest man dort ab.
    "smtp":    Die E-Mail geht an einen lokalen Mailserver (config.SMTP_HOST/SMTP_PORT).
"""

import smtplib
from email.message import EmailMessage

from app import config


def send_mail(to: str, subject: str, body: str) -> None:
    """Verschickt eine einfache Text-E-Mail.

    Args:
        to: Empfängeradresse.
        subject: Betreff.
        body: Text der E-Mail (ohne HTML).

    Raises:
        OSError: im Modus "smtp", wenn der Mailserver nicht erreichbar ist
            (smtplib.SMTPException ist eine Unterklasse davon).
    """
    if config.MAIL_MODE == "smtp":
        message = EmailMessage()
        message["From"] = config.MAIL_SENDER
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.send_message(message)
        return

    # Modus "console": gut sichtbar im Terminal ausgeben
    print(
        "\n" + "=" * 60
        + f"\nE-MAIL (nur im Terminal, MAIL_MODE = 'console')\nAn:      {to}\nBetreff: {subject}\n"
        + "-" * 60 + f"\n{body}\n" + "=" * 60 + "\n",
        flush=True,
    )
