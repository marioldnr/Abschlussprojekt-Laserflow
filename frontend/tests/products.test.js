/**
 * Tests für js/modules/products.js (Produktdaten, Suche, Sortierung, Preisformat)
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { PRODUCTS, findProduct, filterProducts, formatPrice, formatDimensions, listCategories } from "../js/modules/products.js";

test("formatPrice: Cent werden als Euro mit Komma angezeigt", () => {
  // Intl setzt ein geschütztes Leerzeichen vor das €-Zeichen, darum normalisieren.
  const normalize = (text) => text.replace(/\s/g, " ");
  assert.equal(normalize(formatPrice(2490)), "24,90 €");
  assert.equal(normalize(formatPrice(690)), "6,90 €");
  assert.equal(normalize(formatPrice(0)), "0,00 €");
});

test("formatDimensions: Millimeter werden als Zentimeter angezeigt", () => {
  const text = formatDimensions({ width_mm: 115, height_mm: 95, depth_mm: 110 });
  assert.equal(text, "11,5 × 9,5 × 11 cm (B × H × T)");
});

test("findProduct: findet per Zahl und per Text aus der Adresse", () => {
  assert.equal(findProduct(2).id, 2);
  assert.equal(findProduct("2").id, 2);
});

test("findProduct: ungültige oder unbekannte IDs ergeben null", () => {
  for (const value of [null, "", "abc", "2.5", 999, "<script>"]) {
    assert.equal(findProduct(value), null, String(value));
  }
});

test("filterProducts: Suche findet unabhängig von Groß-/Kleinschreibung", () => {
  const result = filterProducts(PRODUCTS, { query: "TELEFON" });
  assert.deepEqual(result.map((p) => p.slug), ["telefonzelle"]);
  assert.equal(filterProducts(PRODUCTS, { query: "gibtsnicht" }).length, 0);
});

test("filterProducts: Kategorie-Filter und leere Kategorie (= alle)", () => {
  assert.ok(filterProducts(PRODUCTS, { category: "Deko" }).every((p) => p.category === "Deko"));
  assert.equal(filterProducts(PRODUCTS, { category: "" }).length, PRODUCTS.length);
});

test("filterProducts: Sortierung nach Preis, Eingabeliste bleibt unverändert", () => {
  const before = PRODUCTS.map((p) => p.id);
  const asc = filterProducts(PRODUCTS, { sort: "preis-auf" }).map((p) => p.price_cent);
  const desc = filterProducts(PRODUCTS, { sort: "preis-ab" }).map((p) => p.price_cent);
  assert.deepEqual(asc, [...asc].sort((a, b) => a - b));
  assert.deepEqual(desc, [...desc].sort((a, b) => b - a));
  assert.deepEqual(PRODUCTS.map((p) => p.id), before);
});

test("Produktdaten: Pflichtfelder wie in der Tabelle products, Preise in ganzen Cent", () => {
  const ids = new Set();
  for (const product of PRODUCTS) {
    assert.ok(!ids.has(product.id), "IDs eindeutig");
    ids.add(product.id);
    assert.ok(Number.isInteger(product.price_cent) && product.price_cent > 0);
    for (const field of ["width_mm", "height_mm", "depth_mm"]) assert.ok(Number.isInteger(product[field]));
    assert.ok(product.images.length >= 1, "mindestens ein Bild");
  }
  assert.deepEqual(listCategories(), [...new Set(PRODUCTS.map((p) => p.category))]);
});
