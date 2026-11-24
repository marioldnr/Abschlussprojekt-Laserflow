/**
 * LaserFlow – products.js (Produktdaten für Katalog und Produktseite)
 *
 * Die Produkte kommen aus der Datenbank: loadProducts() holt sie einmal über
 * GET /api/products (Modul app/catalog) und legt sie in PRODUCTS ab. Die Seiten lesen
 * danach PRODUCTS wie vorher. PRODUCTS ist bewusst immer dasselbe Array-Objekt
 * (es wird gefüllt, nie neu zugewiesen), damit cart-drawer.js über findProduct weiter
 * funktioniert, ohne geändert zu werden.
 *
 * Die API liefert Felder wie in der Tabelle "products" (Preise in Cent, Maße in mm).
 * Hier kommen nur die Felder dazu, die die Oberfläche braucht: category, material,
 * has_customer_image.
 *
 * Material ist für alle Produkte gleich (US14) und steht deshalb als Konstante hier.
 */

import { requestJson } from "./api-client.js";

/** Material aller Produkte (laut US14 gleich für alle). */
export const MATERIAL = "Sperrholz, 3 mm";

/** Produktart, bei der der Kunde ein eigenes Bild hochlädt (US04). */
const PRODUCT_TYPE_CUSTOMER_IMAGE = "customer_image";

/**
 * @typedef {Object} Product
 * @property {number} id
 * @property {string} name
 * @property {string|null} product_type   "customer_image" oder "finished" (aus der API)
 * @property {string} category            Anzeige für den Filter: "Mit eigenem Bild" oder "Fertige Produkte"
 * @property {boolean} has_customer_image true, wenn der Kunde ein eigenes Bild hochlädt
 * @property {string} short_description   ein Satz für Kachel und Kopf der Produktseite
 * @property {string|null} description    ausführlicher Text für die Produktseite
 * @property {number} width_mm
 * @property {number} height_mm
 * @property {number|null} depth_mm       fehlt bei flachen Produkten
 * @property {number} price_cent
 * @property {string} material
 * @property {boolean} is_sold_out
 * @property {string[]} images            Bildpfade, das erste ist das Titelbild
 */

/**
 * Zwischenspeicher aller Produkte für die Seiten. Wird von loadProducts() bzw. setProducts() gefüllt.
 * @type {Product[]}
 */
export const PRODUCTS = [];

/** Merkt sich den Ladevorgang, damit Seiten nicht mehrfach laden. */
let loadingPromise = null;

/** Bild, wenn ein Produkt (noch) kein Foto hat. */
export const FALLBACK_IMAGE = "img/logo/logo-auf-dunkel.svg";

/**
 * Wandelt ein Produkt aus der API in die Form um, die die Seiten brauchen.
 * Warum eine eigene Funktion: Die Anzeige-Kategorie leitet sich aus der Produktart ab,
 * weil es keine Kategorie-Spalte in der Datenbank gibt.
 * @param {object} apiProduct Produkt aus GET /api/products
 * @returns {Product}
 */
export function toViewProduct(apiProduct) {
  const hasCustomerImage = apiProduct.product_type === PRODUCT_TYPE_CUSTOMER_IMAGE;
  const description = apiProduct.description ?? "";
  const shortText = apiProduct.short_description ?? "";
  return {
    ...apiProduct,
    // Ohne Foto ein neutrales Bild, damit Kachel und Galerie nicht "kaputt" aussehen
    images: apiProduct.images?.length ? apiProduct.images : [FALLBACK_IMAGE],
    // Beschreibung ohne den ersten Satz, der schon als Kurzbeschreibung oben steht
    long_description: description.startsWith(shortText) ? description.slice(shortText.length).trim() || description : description,
    category: hasCustomerImage ? "Mit eigenem Bild" : "Fertige Produkte",
    material: MATERIAL,
    has_customer_image: hasCustomerImage,
  };
}

/**
 * Ersetzt den Inhalt von PRODUCTS durch die übergebenen Produkte (aus der API).
 * Für Tests und für loadProducts().
 * @param {object[]} list Produkte wie von der API geliefert
 * @returns {Product[]} PRODUCTS (dasselbe Array)
 */
export function setProducts(list) {
  PRODUCTS.splice(0, PRODUCTS.length, ...list.map(toViewProduct));
  return PRODUCTS;
}

/**
 * Lädt die Produkte einmal vom Backend und füllt PRODUCTS.
 * Ein zweiter Aufruf wartet auf denselben Ladevorgang und lädt nicht erneut.
 * Schlägt das Laden fehl, wird der Merker gelöscht, damit ein späterer Aufruf es erneut versucht.
 *
 * @returns {Promise<Product[]>} PRODUCTS
 * @throws {import("./api-client.js").ApiError} wenn der Server nicht erreichbar ist oder einen Fehler meldet
 */
export async function loadProducts() {
  if (!loadingPromise) {
    loadingPromise = requestJson("/products")
      .then((list) => setProducts(list))
      .catch((error) => {
        loadingPromise = null;
        throw error;
      });
  }
  await loadingPromise;
  return PRODUCTS;
}

const priceFormat = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });

/**
 * Formatiert einen Preis in Cent als Euro-Betrag, z. B. 2490 → "24,90 €".
 * @param {number} cents
 * @returns {string}
 */
export function formatPrice(cents) {
  return priceFormat.format(cents / 100);
}

/**
 * Formatiert die Maße als Text, z. B. "11,5 × 9,5 × 11 cm (B × H × T)".
 * Fehlt die Tiefe (depth_mm ist null), entfällt sie: "4 × 10 cm (B × H)".
 * @param {Product} product
 * @returns {string}
 */
export function formatDimensions(product) {
  const cm = (mm) => (mm / 10).toLocaleString("de-DE");
  if (product.depth_mm == null) {
    return `${cm(product.width_mm)} × ${cm(product.height_mm)} cm (B × H)`;
  }
  return `${cm(product.width_mm)} × ${cm(product.height_mm)} × ${cm(product.depth_mm)} cm (B × H × T)`;
}

/**
 * Sucht ein Produkt über seine ID. Akzeptiert auch die ID als Text (z. B. aus ?id=2).
 * @param {number|string|null} id
 * @param {Product[]} [products]
 * @returns {Product|null} das Produkt oder null, wenn es keins mit dieser ID gibt
 */
export function findProduct(id, products = PRODUCTS) {
  const number = Number(id);
  if (!Number.isInteger(number)) return null;
  return products.find((product) => product.id === number) ?? null;
}

/**
 * Liefert alle Kategorien (Produktarten) in der Reihenfolge ihres ersten Auftretens.
 * @param {Product[]} [products]
 * @returns {string[]}
 */
export function listCategories(products = PRODUCTS) {
  return [...new Set(products.map((product) => product.category))];
}

/**
 * Filtert und sortiert die Produktliste für den Katalog.
 * @param {Product[]} products
 * @param {{ query?: string, category?: string, sort?: "empfohlen"|"preis-auf"|"preis-ab"|"name" }} options
 *   query: Suchtext (Name, Produktart, Kurzbeschreibung; Groß-/Kleinschreibung egal)
 *   category: Produktart (Anzeige-Text) oder "" für alle
 * @returns {Product[]} neue Liste, die Eingabe bleibt unverändert
 */
export function filterProducts(products, { query = "", category = "", sort = "empfohlen" } = {}) {
  const needle = query.trim().toLowerCase();
  const result = products.filter((product) => {
    if (category && product.category !== category) return false;
    if (!needle) return true;
    return [product.name, product.category, product.short_description]
      .some((text) => text.toLowerCase().includes(needle));
  });

  const sorters = {
    "preis-auf": (a, b) => a.price_cent - b.price_cent,
    "preis-ab": (a, b) => b.price_cent - a.price_cent,
    name: (a, b) => a.name.localeCompare(b.name, "de"),
  };
  return sorters[sort] ? result.sort(sorters[sort]) : result;
}
