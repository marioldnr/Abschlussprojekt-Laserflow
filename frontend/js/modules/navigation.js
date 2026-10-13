/**
 * LaserFlow – Hilfsfunktionen für Weiterleitungen
 */

/** Name des URL-Parameters, der festhält, wohin es nach dem Anmelden weitergeht. */
export const RETURN_PARAM = "weiter";

/** Ziel, wenn kein (gültiges) Weiterleitungsziel angegeben ist. */
export const DEFAULT_TARGET = "index.html";

/**
 * Liefert ein sicheres Weiterleitungsziel.
 *
 * Warum: Laut Use Case "Anmelden" soll der Kunde nach dem Login zum gewählten Produkt
 * zurückkehren. Das Ziel steht in der Adresse (?weiter=...). Ohne Prüfung könnte jemand
 * einen Link wie ?weiter=https://boese-seite.de verschicken (Open Redirect).
 * Deshalb sind nur relative Pfade innerhalb von LaserFlow erlaubt.
 *
 * @param {string|null} target Wert aus dem URL-Parameter
 * @returns {string} relativer Pfad innerhalb der Seite oder DEFAULT_TARGET
 */
export function safeReturnTarget(target) {
  if (typeof target !== "string") {
    return DEFAULT_TARGET;
  }
  const value = target.trim();
  const isRelative =
    value !== "" &&
    !value.startsWith("//") &&          // protokoll-relative Adresse auf fremden Server
    !value.startsWith("\\") &&
    !/^[a-z][a-z0-9+.-]*:/i.test(value); // http:, https:, javascript:, data: ...
  return isRelative ? value : DEFAULT_TARGET;
}

/**
 * Liest das Weiterleitungsziel aus der aktuellen Adresse.
 * @param {string} [search] Query-String, standardmäßig window.location.search
 * @returns {string}
 */
export function getReturnTarget(search = window.location.search) {
  return safeReturnTarget(new URLSearchParams(search).get(RETURN_PARAM));
}

/**
 * Baut einen Link zur Anmeldeseite, der danach zur aktuellen Seite zurückführt.
 * @param {string} [currentPath] z. B. "produkt.html?id=3"
 * @returns {string}
 */
export function loginUrlFor(currentPath) {
  const params = new URLSearchParams({ [RETURN_PARAM]: currentPath });
  return `anmelden.html?${params}`;
}
