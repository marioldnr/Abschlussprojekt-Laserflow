/**
 * LaserFlow – Prüfregeln für Formulareingaben (ohne DOM, dadurch testbar)
 *
 * Jede Regel bekommt den Feldwert (und bei Bedarf alle Formularwerte) und gibt
 * entweder `null` (gültig) oder eine deutsche Fehlermeldung zurück.
 *
 * Wichtig: Diese Prüfungen sind nur eine Hilfe für die Nutzer. Das Backend muss
 * dieselben Regeln noch einmal prüfen, weil man Browser-Prüfungen umgehen kann.
 */

/** Mindestlänge für Passwörter. Muss mit der Prüfung im Backend übereinstimmen. */
export const PASSWORD_MIN_LENGTH = 8;

// Bewusst einfache E-Mail-Prüfung: etwas@etwas.endung, ohne Leerzeichen.
// Eine "perfekte" Regex gibt es nicht; die endgültige Prüfung macht die Bestätigungs-E-Mail.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/** Länge des Bestätigungscodes aus der E-Mail. Muss zum Backend passen (app/accounts/service.py). */
export const VERIFICATION_CODE_LENGTH = 4;

// Deutsche Postleitzahl: genau fünf Ziffern.
const POSTAL_CODE_PATTERN = /^\d{5}$/;

// Straße ohne Hausnummer: nur Buchstaben. Zwischen Wörtern ist genau ein Leerzeichen
// oder Bindestrich erlaubt ("Am Ring", "Karl-Marx-Straße"). Keine Ziffern, keine Sonderzeichen.
const STREET_NAME_PATTERN = /^\p{L}+(?:[ -]\p{L}+)*$/u;

// Hausnummer: 1 bis 4 Ziffern, danach höchstens ein Buchstabe ("12", "12a"). Keine Sonderzeichen.
const HOUSE_NUMBER_PATTERN = /^\d{1,4}[a-zA-Z]?$/;

// Namen und Orte: Buchstaben, Leerzeichen, Bindestrich, Apostroph, Punkt.
const NAME_PATTERN = /^[\p{L}][\p{L}\s.'-]*$/u;

/**
 * Pflichtfeld: darf nicht leer sein (Leerzeichen zählen nicht).
 * @param {string} value
 * @returns {string|null}
 */
export function required(value) {
  return String(value ?? "").trim() === "" ? "Bitte fülle dieses Feld aus." : null;
}

/**
 * Prüft das Format einer E-Mail-Adresse.
 * @param {string} value
 * @returns {string|null}
 */
export function email(value) {
  return EMAIL_PATTERN.test(String(value).trim())
    ? null
    : "Bitte gib eine gültige E-Mail-Adresse ein, z. B. name@beispiel.de.";
}

/**
 * Prüft, ob ein neues Passwort sicher genug ist:
 * mindestens PASSWORD_MIN_LENGTH Zeichen, mindestens ein Buchstabe und eine Ziffer.
 * @param {string} value
 * @returns {string|null}
 */
export function strongPassword(value) {
  const text = String(value);
  if (text.length < PASSWORD_MIN_LENGTH) {
    return `Das Passwort muss mindestens ${PASSWORD_MIN_LENGTH} Zeichen lang sein.`;
  }
  if (!/\p{L}/u.test(text) || !/\d/.test(text)) {
    return "Das Passwort muss mindestens einen Buchstaben und eine Ziffer enthalten.";
  }
  return null;
}

/**
 * Erzeugt eine Regel, die prüft, ob der Wert mit einem anderen Feld übereinstimmt.
 * Beispiel: matchesField("password") für "Passwort bestätigen".
 * @param {string} otherFieldName Name des Vergleichsfelds
 * @returns {(value: string, values: Record<string, string>) => string|null}
 */
export function matchesField(otherFieldName) {
  return (value, values) =>
    value === values[otherFieldName] ? null : "Die Passwörter stimmen nicht überein.";
}

/**
 * Vor- und Nachname: nur Buchstaben und übliche Zeichen, 2 bis 50 Zeichen.
 * @param {string} value
 * @returns {string|null}
 */
export function personName(value) {
  const text = String(value).trim();
  if (text.length < 2 || text.length > 50 || !NAME_PATTERN.test(text)) {
    return "Bitte gib einen gültigen Namen ein (nur Buchstaben, 2–50 Zeichen).";
  }
  return null;
}

/**
 * Straßenname ohne Hausnummer: nur Buchstaben, 2 bis 100 Zeichen
 * (Leerzeichen und Bindestrich zwischen Wörtern erlaubt).
 * @param {string} value
 * @returns {string|null}
 */
export function streetName(value) {
  const text = String(value).trim();
  if (/\d/.test(text)) {
    return "Bitte gib die Hausnummer im Feld daneben ein. Die Straße darf keine Zahlen enthalten.";
  }
  if (text.length < 2 || text.length > 100 || !STREET_NAME_PATTERN.test(text)) {
    return "Die Straße darf nur Buchstaben enthalten (Leerzeichen und Bindestrich sind erlaubt), z. B. Musterstraße.";
  }
  return null;
}

/**
 * Hausnummer: Ziffern, danach höchstens ein Buchstabe, z. B. 12 oder 12a.
 * @param {string} value
 * @returns {string|null}
 */
export function houseNumber(value) {
  return HOUSE_NUMBER_PATTERN.test(String(value).trim())
    ? null
    : "Nur Ziffern und höchstens ein Buchstabe, z. B. 12 oder 12a.";
}

/**
 * Deutsche Postleitzahl mit fünf Ziffern.
 * @param {string} value
 * @returns {string|null}
 */
export function postalCode(value) {
  return POSTAL_CODE_PATTERN.test(String(value).trim())
    ? null
    : "Bitte gib eine Postleitzahl mit fünf Ziffern ein.";
}

/**
 * Ortsname: Buchstaben und übliche Zeichen, 2 bis 60 Zeichen.
 * @param {string} value
 * @returns {string|null}
 */
export function city(value) {
  const text = String(value).trim();
  return text.length >= 2 && text.length <= 60 && NAME_PATTERN.test(text)
    ? null
    : "Bitte gib einen gültigen Ort ein.";
}

/**
 * Checkbox muss angehakt sein (z. B. AGB und Datenschutz).
 * @param {boolean} checked
 * @returns {string|null}
 */
export function accepted(checked) {
  return checked === true ? null : "Bitte bestätige, dass du die AGB und die Datenschutzerklärung akzeptierst.";
}

/**
 * Bestätigungscode aus der E-Mail: genau VERIFICATION_CODE_LENGTH Ziffern.
 * @param {string} value
 * @returns {string|null}
 */
export function verificationCode(value) {
  const pattern = new RegExp(`^\\d{${VERIFICATION_CODE_LENGTH}}$`);
  return pattern.test(String(value).trim())
    ? null
    : `Bitte gib den ${VERIFICATION_CODE_LENGTH}-stelligen Code aus der E-Mail ein.`;
}

/**
 * Prüft einen einzelnen Wert gegen eine Liste von Regeln.
 * Die erste Regel, die einen Fehler meldet, gewinnt.
 * @param {*} value Wert des Feldes
 * @param {Array<Function>} rules Regeln, die nacheinander geprüft werden
 * @param {Record<string, *>} [values] alle Formularwerte (für Vergleichsregeln)
 * @returns {string|null} Fehlermeldung oder null
 */
export function validateValue(value, rules, values = {}) {
  for (const rule of rules) {
    const message = rule(value, values);
    if (message) {
      return message;
    }
  }
  return null;
}

/**
 * Prüft alle Felder eines Formulars anhand eines Schemas.
 * @param {Record<string, *>} values Formularwerte, z. B. { email: "...", password: "..." }
 * @param {Record<string, Array<Function>>} schema Regeln pro Feldname
 * @returns {Record<string, string>} Fehlermeldungen pro Feldname (leer, wenn alles gültig ist)
 */
export function validateAll(values, schema) {
  const errors = {};
  for (const [field, rules] of Object.entries(schema)) {
    const message = validateValue(values[field], rules, values);
    if (message) {
      errors[field] = message;
    }
  }
  return errors;
}
