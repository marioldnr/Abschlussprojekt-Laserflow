/**
 * LaserFlow – Popup für Rechtstexte (Issue #38, registrieren.html)
 *
 * Öffnet das <dialog>-Element und lädt den Text aus der verlinkten Seite (z. B. agb.html).
 * Der Text steht dadurch nur an EINER Stelle: im Bereich <article id="legal-text"> der Seite.
 * Abdunkeln, Schließen mit Esc und Fokus im Fenster erledigt der Browser über showModal().
 *
 * Erwartetes HTML (siehe registrieren.html):
 *   - <dialog id="agb-dialog">            das Popup
 *     - [data-agb-title]                   Überschrift, wird durch die der geladenen Seite ersetzt
 *     - [data-agb-loading]                 Hinweis "wird geladen" (hidden)
 *     - [data-agb-error]                   Fehlerhinweis (hidden) mit Link [data-agb-error-link]
 *     - [data-agb-content]                 hier wird der Text eingesetzt
 *     - [data-agb-close]                   Knöpfe zum Schließen
 *   - Links mit data-agb-open und href="agb.html" öffnen das Popup.
 *     Ohne JavaScript öffnen sie die Seite einfach in einem neuen Tab (target="_blank").
 *
 * Bewusste Entscheidungen:
 *   - fetch() wird hier direkt benutzt und nicht über api-client.js: Wir laden eine eigene
 *     HTML-Seite, keine Backend-Schnittstelle (/api/...). api-client.js ist für das Backend da.
 *   - Das Schließen hakt die Checkbox nicht an. Der Kunde muss selbst aktiv zustimmen.
 *   - Jede Seite wird pro Seitenaufruf nur einmal geladen (Zwischenspeicher).
 */

/** id des <dialog>-Elements im HTML. */
export const DIALOG_ID = "agb-dialog";

/** id des Bereichs mit dem Rechtstext in agb.html (und später datenschutz.html). */
export const CONTENT_ID = "legal-text";

/**
 * Lädt eine Seite und liefert ihre Überschrift und den Bereich #legal-text.
 *
 * @param {string} url Adresse der Seite, z. B. "agb.html"
 * @param {object} [options] nur für Tests austauschbar
 * @param {Function} [options.fetchFn] Funktion zum Laden (Standard: fetch)
 * @param {Function} [options.parse] wandelt HTML-Text in ein Dokument um (Standard: DOMParser)
 * @returns {Promise<{title: string, content: Element}>}
 * @throws {Error} wenn die Seite nicht geladen werden kann oder #legal-text fehlt
 */
export async function loadLegalText(url, { fetchFn = fetch, parse = parseHtml } = {}) {
  const response = await fetchFn(url);
  if (!response.ok) {
    throw new Error(`Seite ${url} konnte nicht geladen werden (Status ${response.status}).`);
  }

  const doc = parse(await response.text());
  const content = doc.getElementById(CONTENT_ID);
  if (!content) {
    throw new Error(`In ${url} fehlt der Bereich #${CONTENT_ID}.`);
  }

  const heading = doc.querySelector(".section-head h2");
  return { title: heading ? heading.textContent.trim() : "", content };
}

/** Wandelt HTML-Text in ein Dokument um. DOMParser führt dabei keine Skripte aus. */
function parseHtml(html) {
  return new DOMParser().parseFromString(html, "text/html");
}

/**
 * Verbindet die Links mit dem Popup.
 *
 * @param {Document|Element} root Bereich, in dem gesucht wird (normalerweise document)
 * @param {object} [options] nur für Tests austauschbar
 * @param {Function} [options.load] Funktion zum Laden des Textes (Standard: loadLegalText)
 * @returns {boolean} true, wenn das Popup gefunden und verbunden wurde, sonst false
 */
export function initAgbDialog(root = document, { load = loadLegalText } = {}) {
  const dialog = root.querySelector(`#${DIALOG_ID}`);
  if (!dialog) {
    // Seite ohne Popup: nichts tun statt abstürzen
    return false;
  }

  const title = dialog.querySelector("[data-agb-title]");
  const loading = dialog.querySelector("[data-agb-loading]");
  const error = dialog.querySelector("[data-agb-error]");
  const errorLink = dialog.querySelector("[data-agb-error-link]");
  const content = dialog.querySelector("[data-agb-content]");
  const body = content.parentElement;

  /** Zwischenspeicher: url -> geladener Text, damit jede Seite nur einmal geladen wird. */
  const cache = new Map();

  /**
   * Öffnet das Popup und zeigt den Text der Seite url.
   * @param {string} url Seite mit dem Text, z. B. "agb.html"
   * @param {string} label Linktext ("AGB", "Datenschutzerklärung"), dient als Überschrift,
   *   bis die richtige aus der Seite geladen ist; sonst stünde dort noch die vom letzten Öffnen
   */
  async function open(url, label) {
    if (label) title.textContent = label;
    dialog.showModal();
    if (body) body.scrollTop = 0; // immer oben anfangen

    if (!cache.has(url)) {
      error.hidden = true;
      content.replaceChildren();
      loading.hidden = false;
      try {
        cache.set(url, await load(url));
      } catch {
        loading.hidden = true;
        errorLink.setAttribute("href", url);
        error.hidden = false;
        return;
      }
      loading.hidden = true;
    }

    const { title: text, content: source } = cache.get(url);
    if (text) title.textContent = text;
    error.hidden = true;
    // Kopien einsetzen, damit der Zwischenspeicher unverändert bleibt
    content.replaceChildren(...Array.from(source.childNodes, (node) => node.cloneNode(true)));
  }

  for (const opener of root.querySelectorAll("[data-agb-open]")) {
    opener.addEventListener("click", (event) => {
      // Ohne preventDefault würde der Link die Seite in einem neuen Tab öffnen
      event.preventDefault();
      open(opener.getAttribute("href"), opener.textContent.trim());
    });
  }

  for (const closer of dialog.querySelectorAll("[data-agb-close]")) {
    closer.addEventListener("click", () => dialog.close());
  }

  // Klick auf den abgedunkelten Hintergrund schließt ebenfalls.
  // Der Hintergrund gehört zum <dialog> selbst, deshalb ist das Ziel dann der Dialog
  // und kein Element darin.
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      dialog.close();
    }
  });

  return true;
}
