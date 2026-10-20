/**
 * LaserFlow – Seite "Registrieren" (registrieren.html)
 *
 * Ablauf laut Use Case "Registrieren":
 * 1. Registrierungsdaten eingeben und im Browser prüfen
 *    (E-Mail-Format, Adresse auf Plausibilität, Passwörter auf Übereinstimmung).
 *    Fehler: Feld wird rot markiert, darunter steht, was nicht passt.
 * 2. Daten an das Backend schicken. Das Backend prüft alles noch einmal, prüft die
 *    E-Mail-Eindeutigkeit, speichert das Passwort gehasht und schickt einen 4-stelligen Code.
 *    Findet das Backend Fehler, erscheinen sie ebenfalls am passenden Feld.
 * 3. Erfolg: weiter zur Seite "E-Mail bestätigen" (bestaetigen.html), dort wird der Code eingegeben.
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
import { register, fieldErrorsFromApi } from "./modules/auth-api.js";
import { verifyUrlFor, RETURN_PARAM } from "./modules/navigation.js";
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
    // Weiter zur Code-Eingabe. Das Ziel aus ?weiter= wird mitgenommen.
    const returnTarget = new URLSearchParams(window.location.search).get(RETURN_PARAM);
    window.location.assign(verifyUrlFor(values.email, returnTarget));
  } catch (error) {
    showServerErrors(error);
  } finally {
    setBusy(form, false);
  }
});

/**
 * Zeigt Fehler vom Backend an: Feldfehler direkt am Feld, alles andere über dem Formular.
 * @param {import("./modules/api-client.js").ApiError} error
 */
function showServerErrors(error) {
  if (error.status === 409) {
    // E-Mail schon vergeben
    setFieldError(form, "email", error.message);
    focusFirstError(form);
    return;
  }
  const fieldErrors = error.status === 422 ? fieldErrorsFromApi(error) : {};
  const knownFields = Object.keys(fieldErrors).filter((name) => form.elements.namedItem(name));
  if (knownFields.length > 0) {
    for (const name of knownFields) {
      setFieldError(form, name, fieldErrors[name]);
    }
    focusFirstError(form);
    return;
  }
  showAlert(form, error.message, "error");
}
