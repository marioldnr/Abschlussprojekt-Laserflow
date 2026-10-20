/**
 * LaserFlow – Registrieren, E-Mail bestätigen, Anmelden und Abmelden über das Backend
 *
 * Schnittstelle (Backend: app/accounts/router.py, Details in docs/module/anmeldung.md):
 *
 *   POST /api/auth/register     { email, password, first_name, last_name, street, postal_code, city }
 *                               201 angelegt, Code per E-Mail · 409 E-Mail vergeben · 422 ungültige Felder
 *   POST /api/auth/verify       { email, code }
 *                               200 Kundendaten + Sitzungs-Cookie · 400 Code falsch · 409 schon bestätigt
 *                               410 Code abgelaufen · 429 zu viele Fehlversuche
 *   POST /api/auth/resend-code  { email }            204 (immer)
 *   POST /api/auth/login        { email, password }  200 Kundendaten + Sitzungs-Cookie · 401 falsch · 403 nicht bestätigt
 *   GET  /api/auth/me                                200 Kundendaten · 401 nicht angemeldet
 *   POST /api/auth/logout                            204
 *
 * Die Fehlermeldungen kommen vom Backend schon auf Deutsch ({ "detail": "..." }).
 */

import { requestJson, ApiError } from "./api-client.js";

/** Verständliche Meldungen für die Status-Codes beim Anmelden. */
const LOGIN_MESSAGES = {
  401: "E-Mail-Adresse oder Passwort ist falsch.",
  403: "Dein Konto ist noch nicht bestätigt.",
};

/**
 * Feldnamen im Backend (JSON) → Feldnamen im Formular (name-Attribute im HTML).
 * Felder, die gleich heißen (email, password, street, city), stehen nicht in der Liste.
 */
const FIELD_NAMES = {
  first_name: "firstName",
  last_name: "lastName",
  postal_code: "postalCode",
};

/**
 * Holt die Feldfehler aus einer 422-Antwort des Backends.
 * Format von FastAPI: { detail: [ { loc: ["body", "postal_code"], msg: "..." }, ... ] }
 * @param {ApiError} error
 * @returns {Record<string, string>} Formular-Feldname → Meldung (leer, wenn es keine Feldfehler gibt)
 */
export function fieldErrorsFromApi(error) {
  const errors = {};
  const detail = error?.details?.detail;
  if (!Array.isArray(detail)) {
    return errors;
  }
  for (const item of detail) {
    const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : null;
    if (typeof field === "string" && item.msg) {
      errors[FIELD_NAMES[field] ?? field] = item.msg;
    }
  }
  return errors;
}

/**
 * Meldet einen Kunden an.
 * @param {{ email: string, password: string }} credentials
 * @returns {Promise<object>} Daten des angemeldeten Kunden
 * @throws {ApiError} mit verständlicher Meldung (Status 403 = Konto noch nicht bestätigt)
 */
export async function login({ email, password }) {
  try {
    return await requestJson("/auth/login", {
      method: "POST",
      body: { email: email.trim(), password },
    });
  } catch (error) {
    if (error instanceof ApiError && LOGIN_MESSAGES[error.status]) {
      throw new ApiError(LOGIN_MESSAGES[error.status], error.status, error.details);
    }
    throw error;
  }
}

/**
 * Registriert einen neuen Kunden. Danach verschickt das Backend den Bestätigungscode.
 * @param {{ email: string, password: string, firstName: string, lastName: string,
 *           street: string, postalCode: string, city: string }} data
 * @returns {Promise<object>}
 * @throws {ApiError} Status 409 (E-Mail vergeben) oder 422 (Feldfehler, siehe fieldErrorsFromApi)
 */
export async function register(data) {
  try {
    return await requestJson("/auth/register", {
      method: "POST",
      body: {
        email: data.email.trim(),
        password: data.password,
        first_name: data.firstName.trim(),
        last_name: data.lastName.trim(),
        street: data.street.trim(),
        postal_code: data.postalCode.trim(),
        city: data.city.trim(),
      },
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      throw new ApiError("Diese E-Mail-Adresse ist bereits registriert.", 409, error.details);
    }
    throw error;
  }
}

/**
 * Prüft den Bestätigungscode. Bei Erfolg ist der Kunde danach angemeldet (Cookie).
 * @param {{ email: string, code: string }} data
 * @returns {Promise<object>} Daten des angemeldeten Kunden
 * @throws {ApiError} 400 Code falsch · 409 schon bestätigt · 410 abgelaufen · 429 zu viele Versuche
 */
export async function verifyCode({ email, code }) {
  return requestJson("/auth/verify", {
    method: "POST",
    body: { email: email.trim(), code: code.trim() },
  });
}

/**
 * Fordert einen neuen Bestätigungscode an. Der alte gilt danach nicht mehr.
 * @param {string} email
 * @returns {Promise<null>}
 */
export async function resendCode(email) {
  return requestJson("/auth/resend-code", { method: "POST", body: { email: email.trim() } });
}

/**
 * Fragt, wer gerade angemeldet ist.
 * @returns {Promise<object|null>} Kundendaten oder null, wenn niemand angemeldet ist
 * @throws {ApiError} nur bei anderen Fehlern (z. B. Server nicht erreichbar)
 */
export async function getCurrentUser() {
  try {
    return await requestJson("/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

/**
 * Meldet den Kunden ab (Sitzung im Backend beenden, Cookie löschen).
 * @returns {Promise<null>}
 */
export async function logout() {
  return requestJson("/auth/logout", { method: "POST" });
}
