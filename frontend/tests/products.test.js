/**
 * Tests für js/modules/products.js (Produktdaten, Umwandlung aus der API, Suche, Sortierung, Preisformat)
 *
 * Die Testdaten sind Produkte in der Form, wie GET /api/products sie liefert.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  PRODUCTS,
  MATERIAL,
  findProduct,
  filterProducts,
  formatPrice,
  formatDimensions,
  listCategories,
  loadProducts,
  setProducts,
  toViewProduct,
  FALLBACK_IMAGE,
} from "../js/modules/products.js";

/** Produkte in API-Form (Felder wie in der Tabelle products, Preise in Cent). */
const API_PRODUCTS = [
  {
    id: 1,
    name: "X-Wing Starfighter",
    description: "Detailreiches Modell. Mehr Text.",
    short_description: "Detailreiches Modell.",
    width_mm: 115,
    height_mm: 95,
    depth_mm: 110,
    price_cent: 2490,
    product_type: "finished",
    engraving_width_mm: null,
    engraving_height_mm: null,
    is_sold_out: false,
    images: ["img/produkte/x-wing-1.webp", "img/produkte/x-wing-2.webp"],
  },
  {
    id: 2,
    name: "Britische Telefonzelle",
    description: "Klassische Telefonzelle. Mit Gravur.",
    short_description: "Klassische Telefonzelle.",
    width_mm: 40,
    height_mm: 100,
    depth_mm: 40,
    price_cent: 1490,
    product_type: "finished",
    engraving_width_mm: null,
    engraving_height_mm: null,
    is_sold_out: true,
    images: ["img/produkte/telefonzelle-1.webp"],
  },
  {
    id: 3,
    name: "Gravurplatte (Demo)",
    description: "Holzplatte für deine Gravur.",
    short_description: "Holzplatte für deine Gravur.",
    width_mm: 100,
    height_mm: 80,
    depth_mm: null, // flache Platte ohne Tiefenangabe
    price_cent: 1290,
    product_type: "customer_image",
    engraving_width_mm: 80,
    engraving_height_mm: 60,
    is_sold_out: false,
    images: ["img/produkte/gravurplatte-platzhalter.svg"],
  },
];

/** Stellt die Testdaten in PRODUCTS bereit. Jeder Test setzt sie selbst, damit die Tests unabhängig sind. */
function useTestProducts() {
  setProducts(API_PRODUCTS);
}

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

test("formatDimensions: ohne Tiefe nur Breite und Höhe", () => {
  const text = formatDimensions({ width_mm: 100, height_mm: 80, depth_mm: null });
  assert.equal(text, "10 × 8 cm (B × H)");
});

test("toViewProduct: Produktart wird zu Kategorie und Upload-Kennzeichen", () => {
  const custom = toViewProduct(API_PRODUCTS[2]);
  assert.equal(custom.category, "Mit eigenem Bild");
  assert.equal(custom.has_customer_image, true);

  const finished = toViewProduct(API_PRODUCTS[0]);
  assert.equal(finished.category, "Fertige Produkte");
  assert.equal(finished.has_customer_image, false);
  assert.equal(finished.material, MATERIAL);
});

test("setProducts: füllt PRODUCTS in place und behält dasselbe Array", () => {
  const same = PRODUCTS;
  useTestProducts();
  assert.equal(PRODUCTS, same);
  assert.equal(PRODUCTS.length, 3);
  assert.equal(PRODUCTS[0].category, "Fertige Produkte");
});

test("findProduct: findet per Zahl und per Text aus der Adresse", () => {
  useTestProducts();
  assert.equal(findProduct(2).id, 2);
  assert.equal(findProduct("2").id, 2);
});

test("findProduct: ungültige oder unbekannte IDs ergeben null", () => {
  useTestProducts();
  for (const value of [null, "", "abc", "2.5", 999, "<script>"]) {
    assert.equal(findProduct(value), null, String(value));
  }
});

test("filterProducts: Suche findet unabhängig von Groß-/Kleinschreibung", () => {
  useTestProducts();
  const result = filterProducts(PRODUCTS, { query: "TELEFON" });
  assert.deepEqual(result.map((p) => p.id), [2]);
  assert.equal(filterProducts(PRODUCTS, { query: "gibtsnicht" }).length, 0);
});

test("filterProducts: Filter nach Produktart und leere Produktart (= alle)", () => {
  useTestProducts();
  const custom = filterProducts(PRODUCTS, { category: "Mit eigenem Bild" });
  assert.deepEqual(custom.map((p) => p.id), [3]);
  assert.equal(filterProducts(PRODUCTS, { category: "" }).length, PRODUCTS.length);
  assert.deepEqual(listCategories(PRODUCTS), ["Fertige Produkte", "Mit eigenem Bild"]);
});

test("filterProducts: Sortierung nach Preis, Eingabeliste bleibt unverändert", () => {
  useTestProducts();
  const before = PRODUCTS.map((p) => p.id);
  const asc = filterProducts(PRODUCTS, { sort: "preis-auf" }).map((p) => p.price_cent);
  const desc = filterProducts(PRODUCTS, { sort: "preis-ab" }).map((p) => p.price_cent);
  assert.deepEqual(asc, [...asc].sort((a, b) => a - b));
  assert.deepEqual(desc, [...desc].sort((a, b) => b - a));
  assert.deepEqual(PRODUCTS.map((p) => p.id), before);
});

test("Produktdaten: Pflichtfelder wie in der Tabelle products, Preise in ganzen Cent", () => {
  useTestProducts();
  const ids = new Set();
  for (const product of PRODUCTS) {
    assert.ok(!ids.has(product.id), "IDs eindeutig");
    ids.add(product.id);
    assert.ok(Number.isInteger(product.price_cent) && product.price_cent > 0);
    for (const field of ["width_mm", "height_mm"]) assert.ok(Number.isInteger(product[field]));
    assert.ok(product.depth_mm === null || Number.isInteger(product.depth_mm));
    assert.ok(product.images.length >= 1, "mindestens ein Bild");
  }
});

// Die Ladetests kommen ans Ende: loadProducts() merkt sich seinen Ladevorgang im Modul.
test("loadProducts: nach einem Fehler wird beim nächsten Aufruf erneut geladen", async () => {
  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    throw new TypeError("Netzwerkfehler");
  };
  try {
    await assert.rejects(loadProducts(), { name: "ApiError", status: 0 });
    await assert.rejects(loadProducts(), { name: "ApiError", status: 0 });
    assert.equal(calls, 2);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("loadProducts: lädt einmal über GET /api/products und füllt PRODUCTS", async () => {
  const originalFetch = globalThis.fetch;
  const requested = [];
  globalThis.fetch = async (url, options) => {
    requested.push({ url, method: options.method });
    return { ok: true, status: 200, text: async () => JSON.stringify(API_PRODUCTS) };
  };
  try {
    const first = await loadProducts();
    const second = await loadProducts();

    assert.equal(requested.length, 1, "zweiter Aufruf lädt nicht erneut");
    assert.deepEqual(requested[0], { url: "/api/products", method: "GET" });
    assert.equal(first, PRODUCTS);
    assert.equal(second, PRODUCTS);
    assert.equal(PRODUCTS.length, 3);
    assert.equal(findProduct(3).has_customer_image, true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("toViewProduct: ohne Foto ein Ersatzbild, Beschreibung ohne den ersten Satz", () => {
  const view = toViewProduct({
    id: 9, name: "Test", product_type: "finished", images: [],
    short_description: "Erster Satz.", description: "Erster Satz. Zweiter Satz.",
  });
  assert.deepEqual(view.images, [FALLBACK_IMAGE]);
  assert.equal(view.long_description, "Zweiter Satz.");
});
