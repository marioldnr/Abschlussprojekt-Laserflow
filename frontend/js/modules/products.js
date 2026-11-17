/**
 * LaserFlow – products.js (Produktdaten für Katalog und Produktseite)
 *
 * Vorläufige, fest eingetragene Produktliste, damit Katalog und Produktseite schon
 * präsentierbar sind. Die Felder heißen wie in der Tabelle "products"
 * (app/catalog/models.py): Preise in Cent, Maße in Millimetern.
 *
 * Später: Sobald es einen Katalog-Endpunkt gibt (z. B. GET /api/products), lädt
 * eine Funktion in api-client.js die Liste vom Backend. Die Seiten rufen dann diese
 * Funktion auf statt PRODUCTS zu lesen; formatPrice, findProduct und filterProducts bleiben.
 *
 * Preise und Maße sind Schätzwerte (Platzhalter) und werden später im Team festgelegt.
 */

/**
 * @typedef {Object} Product
 * @property {number} id
 * @property {string} slug            Kurzname, auch für Bilddateien
 * @property {string} name
 * @property {string} category        Kategorie für den Filter im Katalog
 * @property {string} short_description  ein Satz für Kachel und Kopf der Produktseite
 * @property {string} description     ausführlicher Text für die Produktseite
 * @property {number} width_mm
 * @property {number} height_mm
 * @property {number} depth_mm
 * @property {number} price_cent
 * @property {string} material
 * @property {boolean} is_sold_out
 * @property {string[]} images        Bildpfade, das erste ist das Titelbild
 */

/** @type {Product[]} */
export const PRODUCTS = [
  {
    id: 1,
    slug: "x-wing",
    name: "X-Wing Starfighter",
    category: "Modellbau",
    short_description: "Detailreiches Raumschiff-Modell mit Standfuß und graviertem Namensschild.",
    description:
      "Über 20 lasergeschnittene Einzelteile, fein graviert und präzise ineinander gesteckt. " +
      "Das Modell schwebt auf einem schmalen Stab über dem Standfuß, die Tragflächen stehen in " +
      "der typischen X-Stellung. Vorne sitzt ein graviertes Namensschild. Ein Hingucker für " +
      "Regal, Schreibtisch oder Vitrine.",
    width_mm: 115,
    height_mm: 95,
    depth_mm: 110,
    price_cent: 2490,
    material: "Sperrholz, 3 mm, unbehandelt",
    is_sold_out: false,
    images: [
      "img/produkte/x-wing-1.webp",
      "img/produkte/x-wing-2.webp",
      "img/produkte/x-wing-3.webp",
      "img/produkte/x-wing-4.webp",
    ],
  },
  {
    id: 2,
    slug: "telefonzelle",
    name: "Britische Telefonzelle",
    category: "Deko",
    short_description: "Klassische Telefonzelle mit Sprossenfenstern und Gravur „TELEPHONE“.",
    description:
      "Die berühmte Telefonzelle als Holzmodell: vier Seiten mit ausgeschnittenen Sprossenfenstern, " +
      "dahinter milchige Scheiben, oben die Krone und der Schriftzug „TELEPHONE“. " +
      "Die Wände sind mit Fingerzinken verbunden. Oben offen, dadurch auch als Stifthalter " +
      "oder mit einem LED-Teelicht als kleine Laterne nutzbar.",
    width_mm: 40,
    height_mm: 100,
    depth_mm: 40,
    price_cent: 1490,
    material: "Sperrholz, 3 mm, mit Kunststoffscheiben",
    is_sold_out: false,
    images: ["img/produkte/telefonzelle-1.webp", "img/produkte/telefonzelle-2.webp"],
  },
  {
    id: 3,
    slug: "mini-wc",
    name: "Mini-WC",
    category: "Miniaturen",
    short_description: "Kleine Toilette aus geschichteten Holzlagen – mit Augenzwinkern.",
    description:
      "Aus vielen dünnen Holzschichten aufgebaut, dadurch entsteht die typische Streifenoptik. " +
      "Mit Spülknopf auf dem Spülkasten und Gravur im Becken. " +
      "Ein witziges Geschenk, ein Deko-Objekt für das Puppenhaus oder ein Halter für Büroklammern.",
    width_mm: 30,
    height_mm: 38,
    depth_mm: 45,
    price_cent: 690,
    material: "Sperrholz, 3 mm, verleimt",
    is_sold_out: false,
    images: ["img/produkte/mini-wc-1.webp", "img/produkte/mini-wc-2.webp", "img/produkte/mini-wc-3.webp"],
  },
];

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
 * @param {Product} product
 * @returns {string}
 */
export function formatDimensions(product) {
  const cm = (mm) => (mm / 10).toLocaleString("de-DE");
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
 * Liefert alle Kategorien in der Reihenfolge ihres ersten Auftretens.
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
 *   query: Suchtext (Name, Kategorie, Kurzbeschreibung; Groß-/Kleinschreibung egal)
 *   category: Kategorie oder "" für alle
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
