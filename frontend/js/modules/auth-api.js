/**
 * LaserFlow – Anmelden und Registrieren über das Backend
 *
 * Diese Datei beschreibt die Schnittstelle, die das Frontend vom Backend erwartet.
 * Stand: Das Backend gibt es noch nicht. Wer die Router in app/ umsetzt, hält sich
 * an diese Pfade und Antworten (Details in docs/module/anmeldung.md).
 *
 *   POST /api/auth/login
 *     Body:    { email, password }
 *     200:     { id, email, first_name, ... }   Sitzungs-Cookie wird gesetzt
 *     401:     falsche Zugangsdaten
 *     403:     Konto noch nicht per Link bestätigt
 *
 *   POST /api/auth/register
 *     Body:    { email, password, first_name, last_name, street, postal_code, city }
 *     201:     Konto angelegt, Bestätigungs-E-Mail verschickt
 *     409:     E-Mail-Adresse ist schon registriert
 *     422:     ungültige Daten
 */

import { requestJson, ApiError } from "./api-client.js";

/** Verständliche Meldungen für die Status-Codes beim Anmelden. */
const LOGIN_MESSAGES = {
  401: "E-Mail-Adresse oder Passwort ist falsch.",
  403: "Dein Konto ist noch nicht bestätigt. Bitte klicke auf den Link in unserer E-Mail.",
};

/**
 * Meldet einen Kunden an.
 * @param {{ email: string, password: string }} credentials
 * @returns {Promise<object>} Daten des angemeldeten Kunden
 * @throws {ApiError} mit verständlicher Meldung
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
 * Registriert einen neuen Kunden. Danach verschickt das Backend die Bestätigungs-E-Mail.
 * @param {{ email: string, password: string, firstName: string, lastName: string,
 *           street: string, postalCode: string, city: string }} data
 * @returns {Promise<object>}
 * @throws {ApiError} Status 409, wenn die E-Mail schon registriert ist
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
