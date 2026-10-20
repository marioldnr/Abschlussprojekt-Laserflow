/**
 * LaserFlow – Seite "E-Mail bestätigen" (bestaetigen.html)
 *
 * Ablauf:
 * 1. Die Seite wird nach "Konto erstellen" geöffnet (oder beim Anmelden mit unbestätigtem Konto).
 *    Die E-Mail-Adresse steht in der Adresse: bestaetigen.html?email=...
 * 2. Der Kunde gibt den 4-stelligen Code aus der E-Mail ein.
 *    Fehler (falsch, abgelaufen, zu viele Versuche): Feld rot, Meldung darunter.
 * 3. Richtig: Hinweis "Verifizierung erfolgreich", der Kunde ist angemeldet und wird nach
 *    kurzer Zeit automatisch weitergeleitet (Ziel aus ?weiter=, sonst Startseite).
 * "Code erneut senden" schickt einen neuen Code, der alte gilt dann nicht mehr.
 */

import { required, verificationCode } from "./modules/validation.js";
import { validateForm, enableLiveValidation, showAlert, setBusy, setFieldError, focusFirstError } from "./modules/form.js";
import { verifyCode, resendCode } from "./modules/auth-api.js";
import { getReturnTarget, EMAIL_PARAM } from "./modules/navigation.js";

/** Wie lange der Erfolgshinweis zu sehen ist, bevor es automatisch weitergeht. */
const REDIRECT_DELAY_MS = 3000;

/** Fehler, die zum Code-Feld gehören (Code falsch, abgelaufen, zu viele Versuche). */
const CODE_ERROR_STATUS = [400, 410, 429];

const VERIFY_SCHEMA = {
  code: [required, verificationCode],
};

const params = new URLSearchParams(window.location.search);
const address = (params.get(EMAIL_PARAM) ?? "").trim();

const form = document.getElementById("verify-form");
const intro = document.getElementById("verify-intro");
const successPanel = document.getElementById("verify-success");
const missingPanel = document.getElementById("verify-missing");
const resendButton = document.getElementById("resend-button");
const continueLink = document.getElementById("continue-link");

if (!address) {
  // Ohne E-Mail-Adresse wissen wir nicht, welches Konto bestätigt werden soll.
  form.hidden = true;
  intro.hidden = true;
  missingPanel.hidden = false;
} else {
  intro.querySelector("[data-email]").textContent = address;
  enableLiveValidation(form, VERIFY_SCHEMA);

  // Vom Anmelden hierher geschickt: kurz erklären, warum.
  if (params.get("hinweis") === "nicht-bestaetigt") {
    showAlert(form, "Dein Konto ist noch nicht bestätigt. Wir haben dir einen neuen Code geschickt.", "info");
  }

  form.addEventListener("submit", onSubmit);
  resendButton.addEventListener("click", onResend);
}

/**
 * Code absenden und prüfen lassen.
 * @param {SubmitEvent} event
 */
async function onSubmit(event) {
  event.preventDefault();
  showAlert(form, null);

  const { valid, values } = validateForm(form, VERIFY_SCHEMA);
  if (!valid) return;

  setBusy(form, true);
  try {
    await verifyCode({ email: address, code: values.code });
    showSuccess();
  } catch (error) {
    if (CODE_ERROR_STATUS.includes(error.status)) {
      setFieldError(form, "code", error.message);
      focusFirstError(form);
    } else {
      // z. B. 409 "schon bestätigt" oder Server nicht erreichbar
      showAlert(form, error.message, error.status === 409 ? "info" : "error");
    }
  } finally {
    setBusy(form, false);
  }
}

/** Neuen Code anfordern. Der Button ist kurz gesperrt, damit nicht mehrfach geklickt wird. */
async function onResend() {
  showAlert(form, null);
  resendButton.disabled = true;
  try {
    await resendCode(address);
    setFieldError(form, "code", null);
    form.elements.namedItem("code").value = "";
    showAlert(form, "Wir haben dir einen neuen Code geschickt. Der alte Code gilt nicht mehr.", "info");
  } catch (error) {
    showAlert(form, error.message, "error");
  } finally {
    resendButton.disabled = false;
  }
}

/** Erfolg anzeigen und nach REDIRECT_DELAY_MS automatisch weiterleiten. */
function showSuccess() {
  const target = getReturnTarget();
  continueLink.href = target;
  form.hidden = true;
  intro.hidden = true;
  successPanel.hidden = false;
  successPanel.focus();
  window.setTimeout(() => window.location.assign(target), REDIRECT_DELAY_MS);
}
