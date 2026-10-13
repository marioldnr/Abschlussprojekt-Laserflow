/**
 * LaserFlow – Seite "Anmelden" (anmelden.html)
 *
 * Ablauf laut Use Case "Anmelden":
 * 1. Zugangsdaten im Browser grob prüfen (Pflichtfelder, E-Mail-Format).
 * 2. Zugangsdaten an das Backend schicken (Zugangsdaten prüfen).
 * 3. Fehler: Meldung anzeigen (falsche Daten oder Konto nicht bestätigt).
 * 4. Erfolg: zur vorher gewählten Seite zurückkehren (?weiter=...), sonst zur Startseite.
 */

import { required, email } from "./modules/validation.js";
import { validateForm, enableLiveValidation, initPasswordToggles, showAlert, setBusy } from "./modules/form.js";
import { login } from "./modules/auth-api.js";
import { getReturnTarget, RETURN_PARAM } from "./modules/navigation.js";

/** Prüfregeln pro Feld. Beim Anmelden wird das Passwort nur auf "nicht leer" geprüft. */
const LOGIN_SCHEMA = {
  email: [required, email],
  password: [required],
};

const form = document.getElementById("login-form");

initPasswordToggles(form);
enableLiveValidation(form, LOGIN_SCHEMA);

// Der Link "Registrieren" nimmt das Weiterleitungsziel mit, damit es nach der Registrierung nicht verloren geht.
const registerLink = document.getElementById("register-link");
const returnTarget = new URLSearchParams(window.location.search).get(RETURN_PARAM);
if (registerLink && returnTarget) {
  registerLink.href = `registrieren.html?${new URLSearchParams({ [RETURN_PARAM]: returnTarget })}`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showAlert(form, null);

  const { valid, values } = validateForm(form, LOGIN_SCHEMA);
  if (!valid) return;

  setBusy(form, true);
  try {
    await login({ email: values.email, password: values.password });
    window.location.assign(getReturnTarget());
  } catch (error) {
    showAlert(form, error.message, "error");
    form.elements.namedItem("password").value = "";
    form.elements.namedItem("password").focus();
  } finally {
    setBusy(form, false);
  }
});
