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
# Straße ohne Hausnummer: nur Buchstaben, zwischen Wörtern genau ein Leerzeichen oder Bindestrich
# ("Am Ring", "Karl-Marx-Straße"). Keine Ziffern, keine Sonderzeichen.
STREET_NAME_PATTERN = re.compile(rf"^{_LETTER}+(?:[ -]{_LETTER}+)*$")
# Hausnummer: 1 bis 4 Ziffern, danach höchstens ein Buchstabe ("12", "12a").
HOUSE_NUMBER_PATTERN = re.compile(r"^[0-9]{1,4}[a-zA-Z]?$")


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
    """Straßenname ohne Hausnummer: nur Buchstaben, 2 bis 100 Zeichen.

    Leerzeichen und Bindestrich sind zwischen Wörtern erlaubt, Ziffern und andere
    Sonderzeichen nicht (Plausibilitätsprüfung laut Use Case "Registrieren").
    """
    text = value.strip()
    if any(char in "0123456789" for char in text):
        return "Bitte gib die Hausnummer im Feld daneben ein. Die Straße darf keine Zahlen enthalten."
    if not 2 <= len(text) <= 100 or not STREET_NAME_PATTERN.match(text):
        return "Die Straße darf nur Buchstaben enthalten (Leerzeichen und Bindestrich sind erlaubt), z. B. Musterstraße."
    return None


def check_house_number(value: str) -> str | None:
    """Hausnummer: Ziffern, danach höchstens ein Buchstabe, z. B. 12 oder 12a."""
    if not HOUSE_NUMBER_PATTERN.match(value.strip()):
        return "Nur Ziffern und höchstens ein Buchstabe, z. B. 12 oder 12a."
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
    "house_number": check_house_number,
    "postal_code": check_postal_code,
    "city": check_city,
    "password": check_password,
}


# Felder, die man auf "Mein Konto" ändern kann (US10): wie bei der Registrierung,
# nur ohne E-Mail und Passwort (dafür gibt es eigene Abläufe).
PROFILE_RULES = {field: REGISTRATION_RULES[field] for field in
                 ("first_name", "last_name", "street", "house_number", "postal_code", "city")}


def validate_fields(data: dict[str, str], rules: dict) -> dict[str, str]:
    """Prüft Felder nach einer Regel-Liste. Leere Felder ergeben "Bitte fülle dieses Feld aus.".

    Args:
        data: Feldname → eingegebener Wert.
        rules: Feldname → Prüffunktion (z. B. REGISTRATION_RULES).

    Returns:
        Feldname → Fehlermeldung. Leeres Dictionary, wenn alles gültig ist.
    """
    errors = {}
    for field, rule in rules.items():
        value = data.get(field) or ""
        message = "Bitte fülle dieses Feld aus." if not value.strip() else rule(value)
        if message:
            errors[field] = message
    return errors


def validate_registration(data: dict[str, str]) -> dict[str, str]:
    """Prüft alle Felder der Registrierung (siehe validate_fields)."""
    return validate_fields(data, REGISTRATION_RULES)
