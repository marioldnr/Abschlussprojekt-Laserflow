/**
 * Tests für js/modules/agb-dialog.js (Popup für Rechtstexte auf registrieren.html)
 *
 * Node hat keinen Browser. Deshalb bauen wir kleine Ersatz-Elemente, die nur das können,
 * was das Modul braucht. Das Laden der Seite wird ebenfalls ersetzt (Option "load" bzw. "fetchFn").
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { initAgbDialog, loadLegalText } from "../js/modules/agb-dialog.js";

/** Wartet, bis alle angestoßenen async-Abläufe (z. B. das Laden) fertig sind. */
const flush = () => new Promise((resolve) => setImmediate(resolve));

/** Einfaches Ersatz-Element mit Klick-Ereignissen und Attributen. */
function fakeElement(attributes = {}) {
  const listeners = [];
  return {
    hidden: false,
    textContent: "",
    children: [],
    attributes: { ...attributes },
    addEventListener(type, fn) {
      if (type === "click") listeners.push(fn);
    },
    click(target = this) {
      const event = { target, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
      listeners.forEach((fn) => fn(event));
      return event;
    },
    getAttribute(name) { return this.attributes[name] ?? null; },
    setAttribute(name, value) { this.attributes[name] = value; },
    replaceChildren(...nodes) { this.children = nodes; },
  };
}

/** Geladener Text, wie ihn loadLegalText liefern würde. */
function fakeLegalText(title = "Allgemeine Geschäftsbedingungen") {
  const node = { text: "§ 1 Anbieter", cloneNode() { return { text: this.text }; } };
  return { title, content: { childNodes: [node] } };
}

/** Baut eine Ersatz-Seite mit Popup und einem Link auf agb.html. */
function fakePage({ withDialog = true, load = async () => fakeLegalText() } = {}) {
  const opener = fakeElement({ href: "agb.html" });
  opener.textContent = "AGB";
  const closeX = fakeElement();
  const closeButton = fakeElement();
  const paragraph = fakeElement();
  const title = fakeElement();
  title.textContent = "Allgemeine Geschäftsbedingungen";
  const loading = fakeElement();
  loading.hidden = true;
  const error = fakeElement();
  error.hidden = true;
  const errorLink = fakeElement({ href: "agb.html" });
  const body = { scrollTop: 50 };
  const content = { ...fakeElement(), parentElement: body };

  const parts = {
    "[data-agb-title]": title,
    "[data-agb-loading]": loading,
    "[data-agb-error]": error,
    "[data-agb-error-link]": errorLink,
    "[data-agb-content]": content,
  };
  const dialog = {
    ...fakeElement(),
    open: false,
    showModal() { this.open = true; },
    close() { this.open = false; },
    querySelector: (selector) => parts[selector] ?? null,
    querySelectorAll: (selector) => (selector === "[data-agb-close]" ? [closeX, closeButton] : []),
  };
  const calls = [];
  const countingLoad = async (url) => { calls.push(url); return load(url); };
  const root = {
    querySelector: (selector) => (selector === "#agb-dialog" && withDialog ? dialog : null),
    querySelectorAll: (selector) => (selector === "[data-agb-open]" ? [opener] : []),
  };
  initAgbDialog(root, { load: countingLoad });
  return { root, dialog, opener, closeX, closeButton, paragraph, title, loading, error, errorLink, content, body, calls };
}

// ---------- Öffnen und Laden (Normalfall) ----------

test("Klick auf den AGB-Link öffnet das Popup", () => {
  const { dialog, opener } = fakePage();
  opener.click();
  assert.equal(dialog.open, true);
});

test("Klick auf den AGB-Link öffnet keinen neuen Tab (preventDefault)", () => {
  const { opener } = fakePage();
  assert.equal(opener.click().defaultPrevented, true);
});

test("Der Text wird aus der verlinkten Seite (href) geladen und eingesetzt", async () => {
  const { opener, content, calls, loading } = fakePage();
  opener.click();
  assert.equal(loading.hidden, false, "während des Ladens ist der Hinweis sichtbar");
  await flush();
  assert.deepEqual(calls, ["agb.html"]);
  assert.equal(content.children.length, 1);
  assert.equal(content.children[0].text, "§ 1 Anbieter");
  assert.equal(loading.hidden, true, "nach dem Laden ist der Hinweis weg");
});

test("Die Überschrift kommt aus der geladenen Seite", async () => {
  const { opener, title } = fakePage({ load: async () => fakeLegalText("Datenschutzerklärung") });
  opener.click();
  await flush();
  assert.equal(title.textContent, "Datenschutzerklärung");
});

test("Beim Öffnen steht der Text wieder ganz oben", async () => {
  const { opener, body } = fakePage();
  opener.click();
  await flush();
  assert.equal(body.scrollTop, 0);
});

test("Die Seite wird nur einmal geladen, auch wenn man mehrmals öffnet", async () => {
  const { opener, closeX, calls, content } = fakePage();
  opener.click();
  await flush();
  closeX.click();
  opener.click();
  await flush();
  assert.equal(calls.length, 1);
  assert.equal(content.children.length, 1);
});

test("Während des Ladens steht der Linktext als Überschrift da (nicht die vom letzten Öffnen)", () => {
  const { opener, title } = fakePage({ load: () => new Promise(() => {}) }); // lädt nie fertig
  title.textContent = "Datenschutzerklärung";
  opener.click();
  assert.equal(title.textContent, "AGB");
});

// ---------- Schließen (Benutzerinteraktion) ----------

test("✕ schließt das Popup", () => {
  const { dialog, opener, closeX } = fakePage();
  opener.click();
  closeX.click();
  assert.equal(dialog.open, false);
});

test("'Gelesen und schließen' schließt das Popup", () => {
  const { dialog, opener, closeButton } = fakePage();
  opener.click();
  closeButton.click();
  assert.equal(dialog.open, false);
});

test("Klick auf den abgedunkelten Hintergrund schließt das Popup", () => {
  const { dialog, opener } = fakePage();
  opener.click();
  dialog.click(dialog); // Ziel ist der Dialog selbst = Hintergrund
  assert.equal(dialog.open, false);
});

test("Klick auf den Text im Popup schließt es nicht", () => {
  const { dialog, opener, paragraph } = fakePage();
  opener.click();
  dialog.click(paragraph); // Ziel ist ein Element im Dialog
  assert.equal(dialog.open, true);
});

// ---------- Fehlerfälle ----------

test("Laden schlägt fehl: Fehlerhinweis mit Link auf die Seite, kein Text", async () => {
  const { opener, error, errorLink, content, loading } = fakePage({
    load: async () => { throw new Error("404"); },
  });
  opener.click();
  await flush();
  assert.equal(error.hidden, false);
  assert.equal(errorLink.getAttribute("href"), "agb.html");
  assert.equal(content.children.length, 0);
  assert.equal(loading.hidden, true);
});

test("Nach einem Fehler wird beim nächsten Öffnen erneut geladen", async () => {
  let first = true;
  const { opener, closeX, error, content, calls } = fakePage({
    load: async () => {
      if (first) { first = false; throw new Error("Netzwerk"); }
      return fakeLegalText();
    },
  });
  opener.click();
  await flush();
  closeX.click();
  opener.click();
  await flush();
  assert.equal(calls.length, 2);
  assert.equal(error.hidden, true);
  assert.equal(content.children.length, 1);
});

test("Seite ohne Popup: kein Absturz, Rückgabe false", () => {
  const root = { querySelector: () => null, querySelectorAll: () => [] };
  assert.equal(initAgbDialog(root), false);
});

// ---------- loadLegalText ----------

/** Ersatz für fetch und DOMParser. */
function fakeFetch({ ok = true, status = 200, html = "<html></html>" } = {}) {
  return async () => ({ ok, status, text: async () => html });
}
function fakeParse({ hasContent = true, heading = "Allgemeine Geschäftsbedingungen" } = {}) {
  const content = { id: "legal-text" };
  return () => ({
    getElementById: (id) => (id === "legal-text" && hasContent ? content : null),
    querySelector: (selector) => (selector === ".section-head h2" && heading ? { textContent: ` ${heading} ` } : null),
  });
}

test("loadLegalText: liefert Überschrift und Bereich #legal-text", async () => {
  const result = await loadLegalText("agb.html", { fetchFn: fakeFetch(), parse: fakeParse() });
  assert.equal(result.title, "Allgemeine Geschäftsbedingungen");
  assert.equal(result.content.id, "legal-text");
});

test("loadLegalText: Seite nicht gefunden (404) führt zu einem Fehler", async () => {
  await assert.rejects(
    loadLegalText("fehlt.html", { fetchFn: fakeFetch({ ok: false, status: 404 }), parse: fakeParse() }),
    /404/,
  );
});

test("loadLegalText: fehlender Bereich #legal-text führt zu einem Fehler", async () => {
  await assert.rejects(
    loadLegalText("agb.html", { fetchFn: fakeFetch(), parse: fakeParse({ hasContent: false }) }),
    /legal-text/,
  );
});

test("loadLegalText: Netzwerkfehler wird weitergegeben", async () => {
  const fetchFn = async () => { throw new TypeError("Failed to fetch"); };
  await assert.rejects(loadLegalText("agb.html", { fetchFn, parse: fakeParse() }), TypeError);
});

test("loadLegalText: Seite ohne Überschrift liefert leeren Titel", async () => {
  const result = await loadLegalText("agb.html", { fetchFn: fakeFetch(), parse: fakeParse({ heading: null }) });
  assert.equal(result.title, "");
});
