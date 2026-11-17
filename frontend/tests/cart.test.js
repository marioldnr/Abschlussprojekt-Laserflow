/**
 * Tests für js/modules/cart.js (Warenkorb-Logik ohne DOM)
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  addItem, setQuantity, removeItem, countItems, totalCents, clampQuantity,
  sanitizeCart, loadCart, saveCart, MAX_QUANTITY, STORAGE_KEY,
} from "../js/modules/cart.js";

const prices = { 1: 2490, 2: 1490 };
const find = (id) => (prices[id] ? { price_cent: prices[id] } : null);

/** Kleiner Ersatz für localStorage im Test. */
function fakeStorage(initial = {}) {
  const data = { ...initial };
  return {
    getItem: (key) => (key in data ? data[key] : null),
    setItem: (key, value) => { data[key] = String(value); },
    data,
  };
}

test("addItem: neues Produkt wird mit Menge 1 aufgenommen", () => {
  assert.deepEqual(addItem([], 1), [{ productId: 1, quantity: 1 }]);
});

test("addItem: gleiches Produkt erhöht die Menge statt eine zweite Zeile anzulegen", () => {
  const cart = addItem(addItem([], 1, 2), 1, 3);
  assert.deepEqual(cart, [{ productId: 1, quantity: 5 }]);
});

test("addItem: ändert die übergebene Liste nicht", () => {
  const cart = [{ productId: 1, quantity: 1 }];
  addItem(cart, 1);
  addItem(cart, 2);
  assert.deepEqual(cart, [{ productId: 1, quantity: 1 }]);
});

test("addItem: Menge 0 oder negativ legt nichts hinein", () => {
  assert.deepEqual(addItem([], 1, 0), []);
  assert.deepEqual(addItem([], 1, -3), []);
});

test("Grenzfall: Menge wird auf MAX_QUANTITY begrenzt", () => {
  assert.equal(addItem([], 1, 500)[0].quantity, MAX_QUANTITY);
  const full = [{ productId: 1, quantity: MAX_QUANTITY }];
  assert.equal(addItem(full, 1)[0].quantity, MAX_QUANTITY);
});

test("setQuantity: setzt die Menge, 0 entfernt die Position", () => {
  const cart = [{ productId: 1, quantity: 2 }, { productId: 2, quantity: 1 }];
  assert.deepEqual(setQuantity(cart, 1, 4)[0], { productId: 1, quantity: 4 });
  assert.deepEqual(setQuantity(cart, 1, 0), [{ productId: 2, quantity: 1 }]);
});

test("removeItem: entfernt nur das gewählte Produkt", () => {
  const cart = [{ productId: 1, quantity: 2 }, { productId: 2, quantity: 1 }];
  assert.deepEqual(removeItem(cart, 1), [{ productId: 2, quantity: 1 }]);
  assert.deepEqual(removeItem(cart, 99), cart);
});

test("countItems und totalCents: Summe der Mengen und Gesamtbetrag in Cent", () => {
  const cart = [{ productId: 1, quantity: 2 }, { productId: 2, quantity: 3 }];
  assert.equal(countItems(cart), 5);
  assert.equal(totalCents(cart, find), 2 * 2490 + 3 * 1490);
  assert.equal(countItems([]), 0);
  assert.equal(totalCents([], find), 0);
});

test("totalCents: unbekannte Produkte zählen nicht mit", () => {
  assert.equal(totalCents([{ productId: 99, quantity: 2 }], find), 0);
});

test("clampQuantity: ungültige Werte werden 0, Kommazahlen abgerundet", () => {
  assert.equal(clampQuantity("abc"), 0);
  assert.equal(clampQuantity(NaN), 0);
  assert.equal(clampQuantity(2.7), 2);
});

test("sanitizeCart: verwirft kaputte Einträge aus dem Speicher", () => {
  const data = [
    { productId: 1, quantity: 2 },
    { productId: "2", quantity: 1 },
    { productId: 3, quantity: 0 },
    null,
    { productId: 4, quantity: 999 },
  ];
  assert.deepEqual(sanitizeCart(data), [
    { productId: 1, quantity: 2 },
    { productId: 4, quantity: MAX_QUANTITY },
  ]);
  assert.deepEqual(sanitizeCart("kein Array"), []);
});

test("saveCart und loadCart: Warenkorb überlebt das Speichern", () => {
  const storage = fakeStorage();
  saveCart([{ productId: 1, quantity: 2 }], storage);
  assert.deepEqual(loadCart(storage), [{ productId: 1, quantity: 2 }]);
});

test("loadCart: kaputtes JSON oder fehlender Speicher ergibt leeren Warenkorb", () => {
  assert.deepEqual(loadCart(fakeStorage({ [STORAGE_KEY]: "{kaputt" })), []);
  assert.deepEqual(loadCart(undefined), []);
});
