/**
 * Tests für js/modules/navigation.js (Schutz vor Weiterleitung auf fremde Seiten)
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { safeReturnTarget, getReturnTarget, loginUrlFor, DEFAULT_TARGET } from "../js/modules/navigation.js";

test("safeReturnTarget: relative Pfade innerhalb von LaserFlow sind erlaubt", () => {
  assert.equal(safeReturnTarget("produkt.html?id=3"), "produkt.html?id=3");
  assert.equal(safeReturnTarget("index.html#produkte"), "index.html#produkte");
  assert.equal(safeReturnTarget("/frontend/warenkorb.html"), "/frontend/warenkorb.html");
});

test("safeReturnTarget: fremde Seiten und gefährliche Adressen werden abgelehnt", () => {
  for (const value of [
    "https://boese-seite.de",
    "//boese-seite.de",
    "\\\\boese-seite.de",
    "javascript:alert(1)",
    "JavaScript:alert(1)",
    "data:text/html,hallo",
  ]) {
    assert.equal(safeReturnTarget(value), DEFAULT_TARGET, value);
  }
});

test("safeReturnTarget: fehlender oder leerer Wert führt zur Startseite", () => {
  assert.equal(safeReturnTarget(null), DEFAULT_TARGET);
  assert.equal(safeReturnTarget(""), DEFAULT_TARGET);
  assert.equal(safeReturnTarget("   "), DEFAULT_TARGET);
});

test("getReturnTarget und loginUrlFor arbeiten zusammen", () => {
  const url = loginUrlFor("produkt.html?id=3");
  assert.equal(url, "anmelden.html?weiter=produkt.html%3Fid%3D3");
  assert.equal(getReturnTarget(url.split("?")[1]), "produkt.html?id=3");
});
