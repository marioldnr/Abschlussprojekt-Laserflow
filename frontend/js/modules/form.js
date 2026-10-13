/**
 * LaserFlow – wiederverwendbare Formular-Logik (DOM)
 *
 * Erwartetes HTML pro Feld (siehe docs/design.md, Abschnitt "Formulare"):
 *
 *   <div class="field">
 *     <label class="field-label" for="email">E-Mail</label>
 *     <input class="input" id="email" name="email" aria-describedby="email-error">
 *     <p class="field-error" id="email-error" hidden></p>
 *   </div>
 *
 * Die Prüfregeln selbst stehen in validation.js, hier geht es nur um die Anzeige.
 */

import { validateValue, validateAll } from "./validation.js";

/**
 * Liest alle Werte eines Formulars. Checkboxen werden zu true/false.
 * @param {HTMLFormElement} form
 * @returns {Record<string, string|boolean>}
 */
export function readValues(form) {
  const values = {};
  for (const element of form.elements) {
    if (!element.name) continue;
    values[element.name] = element.type === "checkbox" ? element.checked : element.value;
  }
  return values;
}

/**
 * Zeigt eine Fehlermeldung unter einem Feld an oder entfernt sie (message = null).
 * Setzt aria-invalid, damit Screenreader den Fehler ansagen.
 * @param {HTMLFormElement} form
 * @param {string} name Feldname
 * @param {string|null} message
 */
export function setFieldError(form, name, message) {
  const input = form.elements.namedItem(name);
  if (!input) return;
  const errorElement = form.querySelector(`#${input.id}-error`);
  const field = input.closest(".field");

  input.setAttribute("aria-invalid", message ? "true" : "false");
  field?.classList.toggle("has-error", Boolean(message));
  if (errorElement) {
    errorElement.textContent = message ?? "";
    errorElement.hidden = !message;
  }
}

/**
 * Zeigt alle Fehler an und entfernt Fehler bei inzwischen gültigen Feldern.
 * @param {HTMLFormElement} form
 * @param {Record<string, string>} errors
 * @param {Record<string, Array<Function>>} schema
 */
export function showErrors(form, errors, schema) {
  for (const name of Object.keys(schema)) {
    setFieldError(form, name, errors[name] ?? null);
  }
}

/**
 * Setzt den Fokus auf das erste fehlerhafte Feld.
 * @param {HTMLFormElement} form
 */
export function focusFirstError(form) {
  form.querySelector('[aria-invalid="true"]')?.focus();
}

/**
 * Zeigt einen Hinweis über dem Formular an (z. B. Server-Fehler).
 * @param {HTMLFormElement} form
 * @param {string|null} message null blendet den Hinweis aus
 * @param {"error"|"success"|"info"} [type]
 */
export function showAlert(form, message, type = "error") {
  const alert = form.querySelector("[data-form-alert]");
  if (!alert) return;
  alert.textContent = message ?? "";
  alert.hidden = !message;
  alert.className = `alert alert-${type}`;
}

/**
 * Sperrt den Absende-Button während einer Anfrage, damit nicht doppelt gesendet wird.
 * @param {HTMLFormElement} form
 * @param {boolean} busy
 */
export function setBusy(form, busy) {
  const button = form.querySelector('[type="submit"]');
  if (!button) return;
  if (!button.dataset.label) {
    button.dataset.label = button.textContent;
  }
  button.disabled = busy;
  button.setAttribute("aria-busy", String(busy));
  button.textContent = busy ? "Bitte warten …" : button.dataset.label;
}

/**
 * Prüft Felder schon beim Verlassen (blur). Danach wird ein fehlerhaftes Feld bei
 * jeder Eingabe neu geprüft, damit die Meldung verschwindet, sobald es stimmt.
 *
 * Warum blur Fehler nur anzeigt und nie entfernt: Wer nach einem Fehler direkt auf
 * "Absenden" klickt, löst zuerst blur aus. Würde die Meldung dabei verschwinden, rutscht
 * der Button nach oben, und der Klick landet daneben. Entfernt wird die Meldung deshalb
 * nur beim Tippen (input/change).
 * @param {HTMLFormElement} form
 * @param {Record<string, Array<Function>>} schema
 */
export function enableLiveValidation(form, schema) {
  const validateField = (name) => {
    const values = readValues(form);
    return validateValue(values[name], schema[name], values);
  };

  for (const name of Object.keys(schema)) {
    const input = form.elements.namedItem(name);
    if (!input) continue;

    input.addEventListener("blur", () => {
      const message = validateField(name);
      if (message) setFieldError(form, name, message);
    });

    input.addEventListener(input.type === "checkbox" ? "change" : "input", () => {
      if (input.getAttribute("aria-invalid") === "true") {
        setFieldError(form, name, validateField(name));
      }
    });
  }
}

/**
 * Prüft das ganze Formular, zeigt Fehler an und fokussiert das erste fehlerhafte Feld.
 * @param {HTMLFormElement} form
 * @param {Record<string, Array<Function>>} schema
 * @returns {{ valid: boolean, values: Record<string, string|boolean> }}
 */
export function validateForm(form, schema) {
  const values = readValues(form);
  const errors = validateAll(values, schema);
  showErrors(form, errors, schema);
  const valid = Object.keys(errors).length === 0;
  if (!valid) focusFirstError(form);
  return { valid, values };
}

/**
 * Macht alle Buttons mit [data-password-toggle] funktionsfähig:
 * Klick zeigt bzw. verbirgt das Passwort im Feld davor.
 * @param {ParentNode} [root]
 */
export function initPasswordToggles(root = document) {
  for (const button of root.querySelectorAll("[data-password-toggle]")) {
    const input = button.parentElement.querySelector("input");
    button.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.setAttribute("aria-pressed", String(show));
      button.setAttribute("aria-label", show ? "Passwort verbergen" : "Passwort anzeigen");
    });
  }
}
