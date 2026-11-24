/**
 * Tests für js/modules/auth-gate.js (Anmeldefenster, US03)
 *
 * Node hat keinen Browser: "Wer ist angemeldet?" (getUser) und das Öffnen des
 * Fensters (showGate) werden durch Ersatzfunktionen ausgetauscht.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { requireLogin, gateLinks, currentPage } from "../js/modules/auth-gate.js";

/** Zeichnet auf, ob und mit welchen Links das Fenster geöffnet wurde. */
function fakeGate() {
  const calls = [];
  return { calls, showGate: (links) => calls.push(links) };
}

// ---------- requireLogin ----------

test("Angemeldet: true, kein Fenster", async () => {
  const gate = fakeGate();
  const ok = await requireLogin("produkt.html?id=2", { getUser: async () => ({ id: 1 }), showGate: gate.showGate });
  assert.equal(ok, true);
  assert.equal(gate.calls.length, 0);
});

test("Nicht angemeldet: false, Fenster öffnet mit Rücksprung auf das Produkt", async () => {
  const gate = fakeGate();
  const ok = await requireLogin("produkt.html?id=2", { getUser: async () => null, showGate: gate.showGate });
  assert.equal(ok, false);
  assert.equal(gate.calls.length, 1);
  assert.equal(gate.calls[0].loginHref, "anmelden.html?weiter=produkt.html%3Fid%3D2");
  assert.equal(gate.calls[0].registerHref, "registrieren.html?weiter=produkt.html%3Fid%3D2");
});

test("Server nicht erreichbar: wie nicht angemeldet (false, Fenster)", async () => {
  const gate = fakeGate();
  const ok = await requireLogin("produkt.html?id=2", {
    getUser: async () => { throw new Error("Server nicht erreichbar"); },
    showGate: gate.showGate,
  });
  assert.equal(ok, false);
  assert.equal(gate.calls.length, 1);
});

// ---------- gateLinks ----------

test("gateLinks: fremdes Ziel wird zur Startseite (kein Open Redirect)", () => {
  const links = gateLinks("https://boese-seite.de");
  assert.equal(links.loginHref, "anmelden.html?weiter=index.html");
  assert.equal(links.registerHref, "registrieren.html?weiter=index.html");
});

test("gateLinks: leeres Ziel wird zur Startseite", () => {
  assert.equal(gateLinks("").loginHref, "anmelden.html?weiter=index.html");
});

// ---------- currentPage ----------

test("currentPage: Dateiname mit Parametern, ohne Ordner davor", () => {
  assert.equal(currentPage({ pathname: "/produkt.html", search: "?id=2", hash: "" }), "produkt.html?id=2");
  assert.equal(currentPage({ pathname: "/frontend/katalog.html", search: "", hash: "#filter" }), "katalog.html#filter");
});

test("currentPage: Startseite ohne Dateinamen wird index.html", () => {
  assert.equal(currentPage({ pathname: "/", search: "", hash: "" }), "index.html");
});
