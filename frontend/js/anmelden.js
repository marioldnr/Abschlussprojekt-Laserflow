/**
 * LaserFlow – Seite "Anmelden" (anmelden.html)
 *
 * Ablauf laut Use Case "Anmelden":
 * 1. Zugangsdaten im Browser grob prüfen (Pflichtfelder, E-Mail-Format).
 * 2. Zugangsdaten an das Backend schicken (Zugangsdaten prüfen).
 * 3. Falsche Daten: beide Felder rot, unter dem Passwort steht "E-Mail-Adresse oder Passwort ist falsch".
 *    Welches von beiden falsch ist, verraten wir bewusst nicht (sonst könnte man testen,
 *    welche E-Mail-Adressen registriert sind).
 *    Konto noch nicht bestätigt: neuen Code schicken und zur Code-Eingabe (bestaetigen.html) wechseln.
 * 4. Erfolg: zur vorher gewählten Seite zurückkehren (?weiter=...), sonst zur Startseite.
 */

import { required, email } from "./modules/validation.js";
import {
  validateForm,
  enableLiveValidation,
  initPasswordToggles,
  showAlert,
  setBusy,
  setFieldError,
} from "./modules/form.js";
import { login, resendCode } from "./modules/auth-api.js";
import { getReturnTarget, verifyUrlFor, RETURN_PARAM } from "./modules/navigation.js";

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
    if (error.status === 403) {
      await goToVerification(values.email);
      return;
    }
    if (error.status === 401) {
      markInvalid("email");
      setFieldError(form, "password", error.message);
    } else {
      showAlert(form, error.message, "error");
    }
    form.elements.namedItem("password").value = "";
    form.elements.namedItem("password").focus();
  } finally {
    setBusy(form, false);
  }
});

/**
 * Markiert ein Feld rot, ohne eigene Meldung darunter.
 * Die Markierung verschwindet beim Tippen wieder (enableLiveValidation prüft dann neu).
 * @param {string} name Feldname
 */
function markInvalid(name) {
  const input = form.elements.namedItem(name);
  input.setAttribute("aria-invalid", "true");
  input.closest(".field")?.classList.add("has-error");
}

/**
 * Konto ist noch nicht bestätigt: neuen Code schicken (der alte ist vielleicht abgelaufen)
 * und zur Code-Eingabe wechseln.
 * @param {string} address
 */
async function goToVerification(address) {
  try {
    await resendCode(address);
  } catch {
    // Wenn das Senden scheitert, kann man auf der nächsten Seite "Code erneut senden" klicken.
  }
  window.location.assign(verifyUrlFor(address, returnTarget, { hinweis: "nicht-bestaetigt" }));
}
