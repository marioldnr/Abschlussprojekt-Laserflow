"""Prüfregeln für die Registrierung (Backend-Seite).

Es sind dieselben Regeln und Meldungen wie im Frontend (frontend/js/modules/validation.js).
Warum doppelt? Die Prüfung im Browser kann man umgehen (z. B. mit einem eigenen
Programm, das direkt an die API schickt). Verlässlich ist nur die Prüfung im Backend.
Wer hier eine Regel ändert, ändert sie auch in validation.js.

Jede Regel gibt ``None`` (gültig) oder eine deutsche Fehlermeldung zurück.
"""

import re

# Muss mit PASSWORD_MIN_LENGTH in frontend/js/modules/validation.js übereinstimmen.
PASSWORD_MIN_LENGTH = 8
# Obergrenze, damit niemand riesige Texte zum Hashen schickt.
PASSWORD_MAX_LENGTH = 128

# Python kennt kein \p{L} wie JavaScript. [^\W\d_] heißt "Buchstabe" (auch ä, ö, ü, ß, é ...).
_LETTER = r"[^\W\d_]"
_NAME_CHARS = rf"(?:{_LETTER}|[\s.'-])"

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
POSTAL_CODE_PATTERN = re.compile(r"^[0-9]{5}$")
NAME_PATTERN = re.compile(rf"^{_LETTER}{_NAME_CHARS}*$")
# Straße mit Hausnummer, z. B. "Musterstraße 12", "Am Ring 3a", "Hauptstr. 4-6"
STREET_PATTERN = re.compile(rf"^{_LETTER}{_NAME_CHARS}*\s+[0-9]+[a-zA-Z]?(?:\s*[-/]\s*[0-9]+[a-zA-Z]?)?$")


def check_email(value: str) -> str | None:
    """Prüft das Format einer E-Mail-Adresse (bewusst einfach: etwas@etwas.endung)."""
    text = value.strip()
    if len(text) > 255 or not EMAIL_PATTERN.match(text):
        return "Bitte gib eine gültige E-Mail-Adresse ein, z. B. name@beispiel.de."
    return None


def check_password(value: str) -> str | None:
    """Mindestens 8 Zeichen, mindestens ein Buchstabe und eine Ziffer."""
    if len(value) < PASSWORD_MIN_LENGTH:
        return f"Das Passwort muss mindestens {PASSWORD_MIN_LENGTH} Zeichen lang sein."
    if len(value) > PASSWORD_MAX_LENGTH:
        return f"Das Passwort darf höchstens {PASSWORD_MAX_LENGTH} Zeichen lang sein."
    has_letter = any(char.isalpha() for char in value)
    has_digit = any(char in "0123456789" for char in value)
    if not (has_letter and has_digit):
        return "Das Passwort muss mindestens einen Buchstaben und eine Ziffer enthalten."
    return None


def check_name(value: str) -> str | None:
    """Vor- oder Nachname: nur Buchstaben und übliche Zeichen, 2 bis 50 Zeichen."""
    text = value.strip()
    if not 2 <= len(text) <= 50 or not NAME_PATTERN.match(text):
        return "Bitte gib einen gültigen Namen ein (nur Buchstaben, 2–50 Zeichen)."
    return None


def check_street(value: str) -> str | None:
    """Straße mit Hausnummer (Plausibilitätsprüfung laut Use Case "Registrieren")."""
    text = value.strip()
    if len(text) > 200 or not STREET_PATTERN.match(text):
        return "Bitte gib Straße und Hausnummer an, z. B. Musterstraße 12."
    return None


def check_postal_code(value: str) -> str | None:
    """Deutsche Postleitzahl mit genau fünf Ziffern."""
    if not POSTAL_CODE_PATTERN.match(value.strip()):
        return "Bitte gib eine Postleitzahl mit fünf Ziffern ein."
    return None


def check_city(value: str) -> str | None:
    """Ortsname: Buchstaben und übliche Zeichen, 2 bis 60 Zeichen."""
    text = value.strip()
    if not 2 <= len(text) <= 60 or not NAME_PATTERN.match(text):
        return "Bitte gib einen gültigen Ort ein."
    return None


# Welche Regel zu welchem Feld gehört (Feldnamen wie im JSON der Anfrage).
REGISTRATION_RULES = {
    "first_name": check_name,
    "last_name": check_name,
    "email": check_email,
    "street": check_street,
    "postal_code": check_postal_code,
    "city": check_city,
    "password": check_password,
}


def validate_registration(data: dict[str, str]) -> dict[str, str]:
    """Prüft alle Felder der Registrierung.

    Args:
        data: Feldname → eingegebener Wert, z. B. {"email": "...", "password": "..."}.

    Returns:
        Feldname → Fehlermeldung. Leeres Dictionary, wenn alles gültig ist.
    """
    errors = {}
    for field, rule in REGISTRATION_RULES.items():
        value = data.get(field, "")
        message = "Bitte fülle dieses Feld aus." if not value.strip() else rule(value)
        if message:
            errors[field] = message
    return errors
