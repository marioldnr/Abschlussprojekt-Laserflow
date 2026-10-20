/**
 * Tests für js/modules/navigation.js (Schutz vor Weiterleitung auf fremde Seiten)
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { safeReturnTarget, getReturnTarget, loginUrlFor, verifyUrlFor, DEFAULT_TARGET } from "../js/modules/navigation.js";

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

test("verifyUrlFor: E-Mail, Weiterleitungsziel und Zusatzparameter", () => {
  assert.equal(verifyUrlFor(" a@b.de "), "bestaetigen.html?email=a%40b.de");

  const url = verifyUrlFor("a@b.de", "produkt.html?id=3", { hinweis: "nicht-bestaetigt" });
  const params = new URLSearchParams(url.split("?")[1]);
  assert.equal(params.get("email"), "a@b.de");
  assert.equal(params.get("hinweis"), "nicht-bestaetigt");
  assert.equal(getReturnTarget(url.split("?")[1]), "produkt.html?id=3");
});

test("verifyUrlFor: fremdes Weiterleitungsziel wird zur Startseite", () => {
  const url = verifyUrlFor("a@b.de", "https://boese-seite.de");
  assert.equal(new URLSearchParams(url.split("?")[1]).get("weiter"), DEFAULT_TARGET);
});
