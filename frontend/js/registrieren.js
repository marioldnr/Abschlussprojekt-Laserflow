/**
 * LaserFlow – Seite "Registrieren" (registrieren.html)
 *
 * Ablauf laut Use Case "Registrieren":
 * 1. Registrierungsdaten eingeben und im Browser prüfen
 *    (E-Mail-Format, Adresse auf Plausibilität, Passwörter auf Übereinstimmung).
 * 2. Daten an das Backend schicken. Das Backend prüft die E-Mail-Eindeutigkeit,
 *    speichert das Passwort gehasht und verschickt die Bestätigungs-E-Mail.
 * 3. Erfolg: Hinweis anzeigen, dass die E-Mail bestätigt werden muss.
 */

import {
  required,
  email,
  strongPassword,
  matchesField,
  personName,
  street,
  postalCode,
  city,
  accepted,
  validateValue,
} from "./modules/validation.js";
import {
  validateForm,
  enableLiveValidation,
  initPasswordToggles,
  showAlert,
  setBusy,
  setFieldError,
  focusFirstError,
  readValues,
} from "./modules/form.js";
import { register } from "./modules/auth-api.js";
import { initAgbDialog } from "./modules/agb-dialog.js";

/** Prüfregeln pro Feld (Feldnamen = name-Attribute im HTML). */
const REGISTER_SCHEMA = {
  firstName: [required, personName],
  lastName: [required, personName],
  email: [required, email],
  street: [required, street],
  postalCode: [required, postalCode],
  city: [required, city],
  password: [required, strongPassword],
  passwordConfirm: [required, matchesField("password")],
  terms: [accepted],
};

const form = document.getElementById("register-form");
const successPanel = document.getElementById("register-success");

initPasswordToggles(form);
initAgbDialog(); // AGB-Popup (Issue #38)
enableLiveValidation(form, REGISTER_SCHEMA);

// Wenn das Passwort geändert wird, muss die Bestätigung neu geprüft werden.
form.elements.namedItem("password").addEventListener("input", () => {
  const confirm = form.elements.namedItem("passwordConfirm");
  if (confirm.value) {
    const values = readValues(form);
    setFieldError(form, "passwordConfirm", validateValue(values.passwordConfirm, REGISTER_SCHEMA.passwordConfirm, values));
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showAlert(form, null);

  const { valid, values } = validateForm(form, REGISTER_SCHEMA);
  if (!valid) return;

  setBusy(form, true);
  try {
    await register(values);
    showSuccess(values.email);
  } catch (error) {
    if (error.status === 409) {
      // E-Mail schon vergeben: Fehler direkt am Feld anzeigen
      setFieldError(form, "email", error.message);
      focusFirstError(form);
    } else {
      showAlert(form, error.message, "error");
    }
  } finally {
    setBusy(form, false);
  }
});

/**
 * Ersetzt das Formular durch den Hinweis "Bitte E-Mail bestätigen".
 * @param {string} address die eingegebene E-Mail-Adresse
 */
function showSuccess(address) {
  successPanel.querySelector("[data-email]").textContent = address.trim();
  form.hidden = true;
  successPanel.hidden = false;
  successPanel.focus();
}
