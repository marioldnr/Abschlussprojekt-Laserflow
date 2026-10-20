/**
 * LaserFlow – "Mein Konto" über das Backend (US10)
 *
 * Schnittstelle (Backend: app/accounts/account_router.py, Details in docs/module/konto.md).
 * Alle Aufrufe brauchen eine Anmeldung, sonst kommt 401.
 *
 *   GET    /api/account                    → Kontodaten
 *   PUT    /api/account/profile            { first_name, last_name, street, house_number, postal_code, city }
 *   PUT    /api/account/password           { current_password, new_password }       204
 *   POST   /api/account/email              { new_email, password }                  202 { pending_email }
 *   POST   /api/account/email/verify       { code }                                 → Kontodaten
 *   POST   /api/account/email/resend-code                                           204
 *   DELETE /api/account/email                                                       204 (Änderung abbrechen)
 *   PUT    /api/account/avatar             Bilddatei als Body                       { avatar_url }
 *   DELETE /api/account/avatar                                                      204
 *   POST   /api/account/delete             { password }                             204
 *
 * Feldfehler (422) liefert das Backend wie bei der Registrierung, fieldErrorsFromApi()
 * aus auth-api.js ordnet sie den Formularfeldern zu.
 */

import { requestJson } from "./api-client.js";

/** Größte erlaubte Bilddatei. Muss zu AVATAR_MAX_BYTES in app/config.py passen. */
export const AVATAR_MAX_BYTES = 5 * 1024 * 1024;

/** Erlaubte Bildformate für das Profilbild. */
export const AVATAR_TYPES = ["image/jpeg", "image/png", "image/webp"];

/**
 * Prüft eine Bilddatei schon im Browser (das Backend prüft noch einmal).
 * @param {{ size: number, type: string }} file
 * @returns {string|null} Fehlermeldung oder null
 */
export function checkAvatarFile(file) {
  if (!file) return "Bitte wähle ein Bild aus.";
  if (!AVATAR_TYPES.includes(file.type)) return "Bitte wähle ein Bild im Format JPG, PNG oder WebP.";
  if (file.size > AVATAR_MAX_BYTES) return "Das Bild darf höchstens 5 MB groß sein.";
  return null;
}

/** @returns {Promise<object>} alle Daten für "Mein Konto" */
export function getAccount() {
  return requestJson("/account");
}

/**
 * @param {{ firstName: string, lastName: string, street: string, houseNumber: string,
 *           postalCode: string, city: string }} data Werte aus dem Formular
 * @returns {Promise<object>} die gespeicherten Kontodaten
 */
export function updateProfile(data) {
  return requestJson("/account/profile", {
    method: "PUT",
    body: {
      first_name: data.firstName.trim(),
      last_name: data.lastName.trim(),
      street: data.street.trim(),
      house_number: data.houseNumber.trim(),
      postal_code: data.postalCode.trim(),
      city: data.city.trim(),
    },
  });
}

/** @param {{ currentPassword: string, newPassword: string }} data */
export function changePassword({ currentPassword, newPassword }) {
  return requestJson("/account/password", {
    method: "PUT",
    body: { current_password: currentPassword, new_password: newPassword },
  });
}

/** @param {{ newEmail: string, password: string }} data */
export function requestEmailChange({ newEmail, password }) {
  return requestJson("/account/email", { method: "POST", body: { new_email: newEmail.trim(), password } });
}

/** @param {string} code */
export function confirmEmailChange(code) {
  return requestJson("/account/email/verify", { method: "POST", body: { code: code.trim() } });
}

export function resendEmailChangeCode() {
  return requestJson("/account/email/resend-code", { method: "POST" });
}

export function cancelEmailChange() {
  return requestJson("/account/email", { method: "DELETE" });
}

/** @param {Blob} file Bilddatei aus <input type="file"> */
export function uploadAvatar(file) {
  return requestJson("/account/avatar", { method: "PUT", file });
}

export function removeAvatar() {
  return requestJson("/account/avatar", { method: "DELETE" });
}

/** @param {string} password zur Bestätigung */
export function deleteAccount(password) {
  return requestJson("/account/delete", { method: "POST", body: { password } });
}
