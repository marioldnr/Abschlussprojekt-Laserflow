/**
 * Tests für js/modules/product-admin.js (Produkte verwalten, US14): Filter, Suche, Status, Produktart.
 *
 * Die Testdaten sind Produkte in der Form, wie GET /api/products/manage sie liefert.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  MANAGE_FILTERS,
  filterManagedProducts,
  productStatusLabels,
  productTypeLabel,
} from "../js/modules/product-admin.js";

/** Vier Produkte: normal, ausverkauft, ausgeblendet, ausverkauft und ausgeblendet. */
const PRODUCTS = [
  { id: 1, name: "X-Wing Starfighter", product_type: "finished", price_cent: 2490, is_sold_out: false, is_hidden: false, images: [] },
  { id: 2, name: "Britische Telefonzelle", product_type: "finished", price_cent: 1490, is_sold_out: true, is_hidden: false, images: [] },
  { id: 3, name: "Holzbrett geheim", product_type: "finished", price_cent: 990, is_sold_out: false, is_hidden: true, images: [] },
  { id: 4, name: "Gravurplatte", product_type: "customer_image", price_cent: 1290, is_sold_out: true, is_hidden: true, images: [] },
];

const names = (list) => list.map((product) => product.id);

test("MANAGE_FILTERS enthält die vier Filter in fester Reihenfolge", () => {
  assert.deepEqual(MANAGE_FILTERS, ["all", "available", "sold-out", "hidden"]);
});

test("filter 'all' gibt alle Produkte zurück", () => {
  assert.deepEqual(names(filterManagedProducts(PRODUCTS, "", "all")), [1, 2, 3, 4]);
});

test("filter 'available' zeigt nur sichtbare, nicht ausverkaufte Produkte", () => {
  assert.deepEqual(names(filterManagedProducts(PRODUCTS, "", "available")), [1]);
});

test("filter 'sold-out' zeigt alle ausverkauften, auch ausgeblendete", () => {
  assert.deepEqual(names(filterManagedProducts(PRODUCTS, "", "sold-out")), [2, 4]);
});

test("filter 'hidden' zeigt alle ausgeblendeten, auch ausverkaufte", () => {
  assert.deepEqual(names(filterManagedProducts(PRODUCTS, "", "hidden")), [3, 4]);
});

test("Suche findet Namen ohne Rücksicht auf Groß- und Kleinschreibung", () => {
  assert.deepEqual(names(filterManagedProducts(PRODUCTS, "STARFIGHTER", "all")), [1]);
  assert.deepEqual(names(filterManagedProducts(PRODUCTS, "  gravur ", "all")), [4]);
});

test("Suche und Filter wirken zusammen", () => {
  assert.deepEqual(names(filterManagedProducts(PRODUCTS, "holz", "hidden")), [3]);
  assert.deepEqual(names(filterManagedProducts(PRODUCTS, "holz", "available")), []);
});

test("leere oder nur aus Leerzeichen bestehende Suche filtert nichts weg", () => {
  assert.equal(filterManagedProducts(PRODUCTS, "   ", "all").length, 4);
});

test("filterManagedProducts ändert die Eingabeliste nicht", () => {
  const copy = JSON.parse(JSON.stringify(PRODUCTS));
  filterManagedProducts(PRODUCTS, "x", "hidden");
  assert.deepEqual(PRODUCTS, copy);
});

test("productStatusLabels: normales Produkt hat keine Plakette", () => {
  assert.deepEqual(productStatusLabels(PRODUCTS[0]), []);
});

test("productStatusLabels: ausverkauft, ausgeblendet und beides", () => {
  assert.deepEqual(productStatusLabels(PRODUCTS[1]), ["Ausverkauft"]);
  assert.deepEqual(productStatusLabels(PRODUCTS[2]), ["Ausgeblendet"]);
  assert.deepEqual(productStatusLabels(PRODUCTS[3]), ["Ausverkauft", "Ausgeblendet"]);
});

test("productTypeLabel unterscheidet Produktarten", () => {
  assert.equal(productTypeLabel("customer_image"), "Mit eigenem Bild");
  assert.equal(productTypeLabel("finished"), "Fertiges Produkt");
  assert.equal(productTypeLabel(null), "Fertiges Produkt");
});
