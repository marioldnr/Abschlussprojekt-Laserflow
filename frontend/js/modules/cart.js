/**
 * LaserFlow – cart.js (Warenkorb-Logik ohne DOM)
 *
 * Der Warenkorb ist eine Liste von Positionen { productId, quantity }.
 * Alle Funktionen hier sind "rein": Sie ändern die übergebene Liste nicht,
 * sondern geben eine neue zurück. Dadurch sind sie einfach zu testen
 * (tests/cart.test.js).
 *
 * Vorläufig speichert loadCart/saveCart den Warenkorb im Browser (localStorage),
 * damit er beim Seitenwechsel erhalten bleibt. Mit der Story "Artikel in den
 * Warenkorb legen" wandert er ins Backend (Tabelle cart_items); dann ersetzen
 * API-Aufrufe loadCart/saveCart, die Rechenfunktionen bleiben gleich.
 * Preise werden bewusst NICHT im Warenkorb gespeichert, sondern immer aus den
 * Produktdaten gelesen. So zeigt der Warenkorb nie einen veralteten Preis.
 */

/** Höchstmenge pro Position (Schutz vor Tippfehlern wie 1000). */
export const MAX_QUANTITY = 20;

/** Schlüssel im localStorage. */
export const STORAGE_KEY = "laserflow.cart";

/**
 * @typedef {{ productId: number, quantity: number }} CartItem
 */

/**
 * Begrenzt eine Menge auf 0 … MAX_QUANTITY und macht eine ganze Zahl daraus.
 * @param {number} quantity
 * @returns {number}
 */
export function clampQuantity(quantity) {
  const number = Math.floor(Number(quantity));
  if (!Number.isFinite(number) || number < 0) return 0;
  return Math.min(number, MAX_QUANTITY);
}

/**
 * Legt ein Produkt in den Warenkorb. Liegt es schon drin, wird die Menge erhöht.
 * @param {CartItem[]} cart
 * @param {number} productId
 * @param {number} [quantity=1]
 * @returns {CartItem[]}
 */
export function addItem(cart, productId, quantity = 1) {
  const existing = cart.find((item) => item.productId === productId);
  if (existing) {
    return setQuantity(cart, productId, existing.quantity + quantity);
  }
  const amount = clampQuantity(quantity);
  return amount > 0 ? [...cart, { productId, quantity: amount }] : cart;
}

/**
 * Setzt die Menge einer Position. Menge 0 entfernt die Position.
 * @param {CartItem[]} cart
 * @param {number} productId
 * @param {number} quantity
 * @returns {CartItem[]}
 */
export function setQuantity(cart, productId, quantity) {
  const amount = clampQuantity(quantity);
  if (amount === 0) return removeItem(cart, productId);
  return cart.map((item) => (item.productId === productId ? { ...item, quantity: amount } : item));
}

/**
 * Entfernt eine Position.
 * @param {CartItem[]} cart
 * @param {number} productId
 * @returns {CartItem[]}
 */
export function removeItem(cart, productId) {
  return cart.filter((item) => item.productId !== productId);
}

/**
 * Anzahl aller Artikel (Summe der Mengen), z. B. für die Zahl am Warenkorb-Icon.
 * @param {CartItem[]} cart
 * @returns {number}
 */
export function countItems(cart) {
  return cart.reduce((sum, item) => sum + item.quantity, 0);
}

/**
 * Gesamtbetrag in Cent. Positionen, deren Produkt es nicht (mehr) gibt, zählen nicht mit.
 * @param {CartItem[]} cart
 * @param {(id: number) => ({ price_cent: number } | null)} findProduct
 * @returns {number}
 */
export function totalCents(cart, findProduct) {
  return cart.reduce((sum, item) => {
    const product = findProduct(item.productId);
    return product ? sum + product.price_cent * item.quantity : sum;
  }, 0);
}

/**
 * Prüft gespeicherte Daten und wirft alles weg, was kein gültiger Eintrag ist
 * (z. B. von Hand im Browser verändert).
 * @param {unknown} data
 * @returns {CartItem[]}
 */
export function sanitizeCart(data) {
  if (!Array.isArray(data)) return [];
  return data
    .filter((item) => item && Number.isInteger(item.productId))
    .map((item) => ({ productId: item.productId, quantity: clampQuantity(item.quantity) }))
    .filter((item) => item.quantity > 0);
}

/**
 * Liest den Warenkorb aus dem Browser. Klappt das nicht (privater Modus, kaputte Daten),
 * gibt es einen leeren Warenkorb statt eines Fehlers.
 * @param {Storage} [storage]
 * @returns {CartItem[]}
 */
export function loadCart(storage = globalThis.localStorage) {
  try {
    return sanitizeCart(JSON.parse(storage.getItem(STORAGE_KEY) ?? "[]"));
  } catch {
    return [];
  }
}

/**
 * Speichert den Warenkorb im Browser. Fehler (z. B. Speicher voll) werden ignoriert.
 * @param {CartItem[]} cart
 * @param {Storage} [storage]
 */
export function saveCart(cart, storage = globalThis.localStorage) {
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(cart));
  } catch {
    // Speichern nicht möglich: Warenkorb gilt dann nur bis zum Neuladen.
  }
}
