/**
 * LaserFlow – zentrale Verbindung zum Backend (FastAPI)
 *
 * Alle Anfragen an den Server laufen über requestJson(). So gibt es nur eine Stelle,
 * an der Adresse, Header und Fehlerbehandlung festgelegt sind.
 */

/** Basis-Pfad der REST-Schnittstelle. Muss zu den Routern im Backend passen. */
export const API_BASE = "/api";

/** Meldung, wenn das Backend nicht antwortet. */
export const UNREACHABLE_MESSAGE = "Der Server ist gerade nicht erreichbar. Bitte versuche es später noch einmal.";

/**
 * Fehler, den das Backend zurückgemeldet hat (HTTP-Status 4xx/5xx)
 * oder der entsteht, wenn der Server gar nicht erreichbar ist (status 0).
 */
export class ApiError extends Error {
  /**
   * @param {string} message Meldung für die Anzeige
   * @param {number} status HTTP-Status, 0 = Server nicht erreichbar
   * @param {*} [details] Rohdaten der Antwort (z. B. Feldfehler von FastAPI)
   */
  constructor(message, status, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

/**
 * Holt eine lesbare Meldung aus einer FastAPI-Fehlerantwort.
 * FastAPI liefert { "detail": "Text" } oder bei Validierungsfehlern
 * { "detail": [ { "msg": "...", "loc": [...] } ] }.
 * @param {*} body
 * @returns {string|null}
 */
export function extractErrorMessage(body) {
  if (!body || body.detail === undefined) {
    return null;
  }
  if (typeof body.detail === "string") {
    return body.detail;
  }
  if (Array.isArray(body.detail) && body.detail.length > 0) {
    return body.detail.map((item) => item.msg).filter(Boolean).join(" ");
  }
  return null;
}

/**
 * Schickt eine JSON-Anfrage an das Backend.
 * @param {string} path Pfad ab API_BASE, z. B. "/auth/login"
 * @param {{ method?: string, body?: object, file?: Blob }} [options]
 *   body: wird als JSON geschickt · file: wird unverändert geschickt (z. B. ein Bild),
 *   mit dem Dateityp als Content-Type. Nur eins von beiden angeben.
 * @returns {Promise<*>} die JSON-Antwort des Servers (oder null bei leerer Antwort)
 * @throws {ApiError} bei Fehlerstatus oder wenn der Server nicht erreichbar ist
 */
export async function requestJson(path, { method = "GET", body, file } = {}) {
  const headers = { Accept: "application/json" };
  let payload;
  if (file) {
    headers["Content-Type"] = file.type || "application/octet-stream";
    payload = file;
  } else if (body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: payload,
      credentials: "same-origin", // Sitzungs-Cookie des Backends mitschicken
    });
  } catch {
    throw new ApiError(UNREACHABLE_MESSAGE, 0);
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null; // z. B. HTML-Fehlerseite statt JSON
    }
  }

  if (!response.ok) {
    // Keine JSON-Antwort bei 404/405/501: Die Schnittstelle gibt es (noch) nicht, z. B. weil
    // die Seite über Live Server statt über FastAPI läuft. Dann wie "nicht erreichbar" behandeln.
    if (data === null && [404, 405, 501].includes(response.status)) {
      throw new ApiError(UNREACHABLE_MESSAGE, 0);
    }
    const message =
      extractErrorMessage(data) ?? "Es ist ein Fehler aufgetreten. Bitte versuche es später noch einmal.";
    throw new ApiError(message, response.status, data);
  }
  return data;
}
