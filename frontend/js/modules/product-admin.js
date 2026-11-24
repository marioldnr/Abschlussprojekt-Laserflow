/**
 * LaserFlow – product-admin.js (Hilfsfunktionen für "Produkte verwalten", US14)
 *
 * Reine Funktionen ohne DOM, damit sie mit node:test getestet werden können.
 * Benutzt von js/produkte-verwalten.js. Die Produkte kommen als Liste aus
 * GET /api/products/manage (Format ManagedProductResponse im Backend).
 */

/** Filter der Verwaltungsliste: alle, verfügbar (sichtbar und nicht ausverkauft), ausverkauft, ausgeblendet. */
export const MANAGE_FILTERS = ["all", "available", "sold-out", "hidden"];

/** Produktart, bei der der Kunde ein eigenes Bild hochlädt (US04). */
const PRODUCT_TYPE_CUSTOMER_IMAGE = "customer_image";

/**
 * @typedef {Object} ManagedProduct
 * @property {number} id
 * @property {string} name
 * @property {string|null} product_type  "customer_image" oder "finished"
 * @property {number} price_cent
 * @property {boolean} is_sold_out
 * @property {boolean} is_hidden
 * @property {string[]} images           Bildpfade, das erste ist das Titelbild
 */

/**
 * Anzeigetext der Produktart.
 * @param {string|null} productType "customer_image" oder "finished"
 * @returns {string} "Mit eigenem Bild" bzw. "Fertiges Produkt"
 */
export function productTypeLabel(productType) {
  return productType === PRODUCT_TYPE_CUSTOMER_IMAGE ? "Mit eigenem Bild" : "Fertiges Produkt";
}

/**
 * Status-Plaketten eines Produkts. Ein Produkt kann beides gleichzeitig haben.
 * @param {ManagedProduct} product
 * @returns {string[]} z. B. ["Ausverkauft", "Ausgeblendet"] oder [] für ein normales Produkt
 */
export function productStatusLabels(product) {
  const labels = [];
  if (product.is_sold_out) labels.push("Ausverkauft");
  if (product.is_hidden) labels.push("Ausgeblendet");
  return labels;
}

/**
 * Filtert die Liste nach Suchtext (Name) und Filter-Knopf.
 *
 * Filter:
 *   "all"        alle Produkte
 *   "available"  sichtbar und nicht ausverkauft (das, was Kunden kaufen können)
 *   "sold-out"   ausverkauft (egal ob sichtbar)
 *   "hidden"     ausgeblendet
 *
 * @param {ManagedProduct[]} list
 * @param {string} query Suchtext, Groß-/Kleinschreibung egal
 * @param {"all"|"available"|"sold-out"|"hidden"} filter
 * @returns {ManagedProduct[]} neue Liste, die Eingabe bleibt unverändert
 */
export function filterManagedProducts(list, query, filter) {
  const text = query.trim().toLowerCase();
  return list.filter((product) => {
    if (filter === "available" && (product.is_hidden || product.is_sold_out)) return false;
    if (filter === "sold-out" && !product.is_sold_out) return false;
    if (filter === "hidden" && !product.is_hidden) return false;
    if (!text) return true;
    return product.name.toLowerCase().includes(text);
  });
}
