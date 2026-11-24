/**
 * LaserFlow – Anmeldefenster (US03, Issue #3)
 *
 * Schützt Aktionen, die nur angemeldete Kunden ausführen dürfen
 * (z. B. „Bild hochladen“, „In den Warenkorb“). Benutzung auf einer Seite:
 *
 *   import { requireLogin } from "./modules/auth-gate.js";
 *   if (!(await requireLogin())) return;
 *
 * Ist jemand angemeldet, liefert requireLogin() true und es passiert nichts.
 * Sonst öffnet sich ein Fenster mit „Anmelden“ und „Registrieren“; beide führen
 * nach erfolgreicher Anmeldung bzw. Bestätigung zurück auf die aktuelle Seite
 * (Parameter ?weiter=, siehe navigation.js). Rückgabe dann false.
 *
 * Bewusste Entscheidungen:
 *   - Server nicht erreichbar → wie „nicht angemeldet“ behandeln (Fenster, false).
 *     Lieber einmal zu oft anmelden lassen als ungeprüft weitermachen.
 *     Die eigentliche Prüfung macht ohnehin das Backend bei jeder Anfrage.
 *   - Das Fenster wird per JavaScript gebaut, damit Seiten wie produkt.html kein
 *     zusätzliches HTML brauchen. Seine Styles stehen in css/auth-gate.css und
 *     werden beim ersten Öffnen automatisch eingebunden.
 *   - Texte nur über textContent, nie als rohes HTML.
 */

import { getCurrentUser } from "./auth-api.js";
import { RETURN_PARAM, safeReturnTarget } from "./navigation.js";

/** id des Fensters im Dokument (es gibt höchstens eins pro Seite). */
export const GATE_ID = "auth-gate";

/** Pfad der Styles, relativ zu den Seiten im Ordner frontend/. */
export const GATE_STYLESHEET = "css/auth-gate.css";

/**
 * Baut die beiden Links des Fensters mit Rücksprung auf returnTarget.
 * @param {string} returnTarget Seite, zu der es danach zurückgeht, z. B. "produkt.html?id=2"
 * @returns {{loginHref: string, registerHref: string}}
 */
export function gateLinks(returnTarget) {
  const params = new URLSearchParams({ [RETURN_PARAM]: safeReturnTarget(returnTarget) });
  return {
    loginHref: `anmelden.html?${params}`,
    registerHref: `registrieren.html?${params}`,
  };
}

/**
 * Liefert die aktuelle Seite als relativen Pfad, z. B. "produkt.html?id=2".
 * @param {Location} [loc] standardmäßig window.location
 * @returns {string}
 */
export function currentPage(loc = globalThis.location) {
  const file = loc.pathname.split("/").pop() || "index.html";
  return `${file}${loc.search}${loc.hash}`;
}

/**
 * Prüft, ob jemand angemeldet ist; öffnet sonst das Anmeldefenster.
 *
 * @param {string} [returnTarget] Rücksprungziel, standardmäßig die aktuelle Seite
 * @param {object} [options] nur für Tests austauschbar
 * @param {Function} [options.getUser] Standard: getCurrentUser aus auth-api.js
 * @param {Function} [options.showGate] Standard: öffnet das echte Fenster
 * @returns {Promise<boolean>} true = angemeldet, weitermachen; false = abbrechen
 */
export async function requireLogin(returnTarget = currentPage(), { getUser = getCurrentUser, showGate = openGate } = {}) {
  let user = null;
  try {
    user = await getUser();
  } catch {
    user = null; // Server nicht erreichbar: wie nicht angemeldet behandeln
  }
  if (user) {
    return true;
  }
  showGate(gateLinks(returnTarget));
  return false;
}

/**
 * Öffnet das Anmeldefenster (baut es beim ersten Aufruf).
 * @param {{loginHref: string, registerHref: string}} links
 */
export function openGate(links) {
  ensureStylesheet();
  const dialog = document.getElementById(GATE_ID) ?? buildGate();
  dialog.querySelector("[data-gate-login]").href = links.loginHref;
  dialog.querySelector("[data-gate-register]").href = links.registerHref;
  if (!dialog.open) {
    dialog.showModal();
  }
}

/** Bindet css/auth-gate.css einmalig ein, falls die Seite es noch nicht lädt. */
function ensureStylesheet() {
  if (document.querySelector(`link[href="${GATE_STYLESHEET}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = GATE_STYLESHEET;
  document.head.append(link);
}

/** Baut das Fenster und hängt es an den body. */
function buildGate() {
  const el = (tag, props = {}) => Object.assign(document.createElement(tag), props);

  const dialog = el("dialog", { id: GATE_ID, className: "auth-gate" });
  dialog.setAttribute("aria-labelledby", `${GATE_ID}-title`);

  const close = el("button", { type: "button", className: "icon-button auth-gate-close", textContent: "✕" });
  close.setAttribute("aria-label", "Fenster schließen");
  close.addEventListener("click", () => dialog.close());

  const title = el("h2", { id: `${GATE_ID}-title`, textContent: "Bitte melde dich an" });
  const text = el("p", {
    textContent: "Um ein Bild hochzuladen oder etwas in den Warenkorb zu legen, brauchst du ein Kundenkonto. Danach geht es direkt hier weiter.",
  });

  const login = el("a", { className: "button button-block", textContent: "Anmelden" });
  login.dataset.gateLogin = "";
  const register = el("a", { className: "text-link", textContent: "Jetzt registrieren" });
  register.dataset.gateRegister = "";
  const hint = el("p", { className: "auth-gate-switch", textContent: "Noch kein Konto? " });
  hint.append(register);

  dialog.append(close, title, text, login, hint);

  // Klick auf den abgedunkelten Hintergrund schließt (Ziel ist dann der Dialog selbst)
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  document.body.append(dialog);
  return dialog;
}
