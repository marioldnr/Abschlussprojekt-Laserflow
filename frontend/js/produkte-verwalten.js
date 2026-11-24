/**
 * LaserFlow – Seite "Produkte verwalten" (produkte-verwalten.html, US14, Anfang)
 *
 * Ablauf:
 * 1. Beim Laden die Produktliste holen (GET /api/products/manage). Sie enthält auch ausgeblendete Produkte.
 *    401 = niemand angemeldet → Hinweis mit Link zur Anmeldung.
 *    403 = angemeldet, aber Kunde → Hinweis, die Liste bleibt verborgen.
 * 2. Ausverkauft: Knopf schickt PUT /api/products/<id>/sold-out mit dem gegenteiligen Wert.
 *    Das geht auch bei ausgeblendeten Produkten.
 * 3. Ausblenden: Rückfrage, dann PUT /api/products/<id>/hidden. Ausblenden ist kein Löschen,
 *    nur ein Flag. Wieder einblenden ist jederzeit möglich.
 * 4. Die Antwort des Backends ersetzt den Eintrag in der Liste, danach wird die Liste neu gezeichnet.
 *
 * Wer Mitarbeiter ist, prüft das Backend bei jeder Anfrage. Das Verstecken der Seite hier ist
 * nur Komfort, kein Schutz.
 */

import { requestJson } from "./modules/api-client.js";
import { loginUrlFor } from "./modules/navigation.js";
import { FALLBACK_IMAGE, formatPrice } from "./modules/products.js";
import { filterManagedProducts, productStatusLabels, productTypeLabel } from "./modules/product-admin.js";

/** Pfade der Schnittstelle (ab /api, siehe api-client.js). */
const PRODUCTS_PATH = "/products";
const MANAGE_PATH = `${PRODUCTS_PATH}/manage`;

/** Alle Produkte, wie zuletzt vom Backend geliefert. */
let products = [];

/** Aktiver Filter der Liste: "all", "available", "sold-out" oder "hidden". */
let activeFilter = "all";

/** IDs der Produkte, für die gerade eine Anfrage läuft (deren Knöpfe sind gesperrt). */
const pendingIds = new Set();

const panel = document.getElementById("manage-panel");
const accessAlert = document.getElementById("manage-access");
const searchInput = document.getElementById("manage-search");
const filterButtons = document.querySelectorAll("[data-filter]");
const statTotal = document.getElementById("stat-total");
const statSoldOut = document.getElementById("stat-sold-out");
const statHidden = document.getElementById("stat-hidden");
const messageBox = document.getElementById("manage-message");
const emptyHint = document.getElementById("manage-empty");
const items = document.getElementById("manage-items");

searchInput.addEventListener("input", renderList);
for (const button of filterButtons) {
  button.addEventListener("click", () => {
    activeFilter = button.dataset.filter;
    for (const other of filterButtons) {
      other.setAttribute("aria-pressed", String(other === button));
    }
    renderList();
  });
}

loadProducts();

/**
 * Holt die Produktliste vom Backend und zeigt Liste und Kennzahlen an.
 * Bei fehlender Berechtigung erscheint stattdessen ein Hinweis.
 */
async function loadProducts() {
  try {
    products = await requestJson(MANAGE_PATH);
  } catch (error) {
    showAccessProblem(error);
    return;
  }
  accessAlert.hidden = true;
  panel.hidden = false;
  renderList();
}

/**
 * Zeigt, warum die Seite nicht benutzt werden kann.
 * @param {import("./modules/api-client.js").ApiError} error
 */
function showAccessProblem(error) {
  panel.hidden = true;
  accessAlert.hidden = false;
  accessAlert.textContent = "";

  if (error.status === 401) {
    // Link per DOM bauen (nicht innerHTML), damit nie fremder Text als HTML ausgeführt wird.
    accessAlert.append("Bitte melde dich als Mitarbeiter an. ");
    const link = document.createElement("a");
    link.className = "text-link";
    link.href = loginUrlFor("produkte-verwalten.html");
    link.textContent = "Zur Anmeldung";
    accessAlert.append(link);
  } else {
    accessAlert.textContent = error.message; // 403: "Diese Seite ist nur für Mitarbeiter und Admins." oder Server nicht erreichbar
  }
}

/** Baut Kennzahlen und Liste neu auf. */
function renderList() {
  statTotal.textContent = products.length;
  statSoldOut.textContent = products.filter((product) => product.is_sold_out).length;
  statHidden.textContent = products.filter((product) => product.is_hidden).length;

  const visible = filterManagedProducts(products, searchInput.value, activeFilter);
  items.replaceChildren(...visible.map(renderItem));

  emptyHint.hidden = visible.length > 0;
  emptyHint.textContent = products.length === 0 ? "Noch keine Produkte angelegt." : "Keine Treffer für diese Suche.";
}

/**
 * Eine Zeile: Vorschaubild, Name, Produktart und Preis, Status-Plaketten, zwei Knöpfe.
 * Texte immer per textContent, nie per innerHTML.
 * @param {import("./modules/product-admin.js").ManagedProduct} product
 * @returns {HTMLLIElement}
 */
function renderItem(product) {
  const busy = pendingIds.has(product.id);

  const item = document.createElement("li");
  item.className = "manage-item";
  item.classList.toggle("is-hidden", product.is_hidden);
  item.classList.toggle("is-sold-out", product.is_sold_out);

  const image = document.createElement("img");
  image.className = "manage-thumb";
  image.src = product.images?.[0] || FALLBACK_IMAGE;
  image.alt = product.name;
  image.loading = "lazy";

  const text = document.createElement("div");
  text.className = "manage-text";
  const name = document.createElement("p");
  name.className = "manage-name";
  name.textContent = product.name;
  const meta = document.createElement("p");
  meta.className = "manage-meta";
  meta.textContent = `${productTypeLabel(product.product_type)} · ${formatPrice(product.price_cent)}`;
  text.append(name, meta);

  const labels = productStatusLabels(product);
  if (labels.length > 0) {
    const badges = document.createElement("p");
    badges.className = "manage-badges";
    for (const label of labels) {
      const badge = document.createElement("span");
      badge.className = "manage-badge";
      badge.textContent = label;
      badges.append(badge);
    }
    text.append(badges);
  }

  const actions = document.createElement("div");
  actions.className = "manage-actions";

  const soldOutButton = createButton(product.is_sold_out ? "Wieder verfügbar" : "Als ausverkauft markieren", busy);
  soldOutButton.addEventListener("click", () =>
    updateProduct(product, `${PRODUCTS_PATH}/${product.id}/sold-out`, { is_sold_out: !product.is_sold_out }, (updated) =>
      updated.is_sold_out ? `„${updated.name}“ ist jetzt ausverkauft.` : `„${updated.name}“ ist wieder verfügbar.`,
    ),
  );

  const hiddenButton = createButton(product.is_hidden ? "Wieder einblenden" : "Ausblenden", busy);
  hiddenButton.addEventListener("click", () => onToggleHidden(product));

  actions.append(soldOutButton, hiddenButton);
  item.append(image, text, actions);
  return item;
}

/**
 * Glas-Knopf für eine Zeile. Während einer Anfrage ist er gesperrt.
 * @param {string} label Beschriftung
 * @param {boolean} disabled true, solange die Zeile auf die Antwort wartet
 * @returns {HTMLButtonElement}
 */
function createButton(label, disabled) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "button button-ghost manage-button";
  button.textContent = label;
  button.disabled = disabled;
  return button;
}

/**
 * Blendet ein Produkt aus oder ein. Ausblenden fragt vorher nach.
 * @param {import("./modules/product-admin.js").ManagedProduct} product
 */
function onToggleHidden(product) {
  if (!product.is_hidden) {
    const confirmed = window.confirm(
      `„${product.name}“ im Katalog ausblenden? Kunden sehen es dann nicht mehr. Du kannst es später wieder einblenden.`,
    );
    if (!confirmed) return;
  }
  updateProduct(product, `${PRODUCTS_PATH}/${product.id}/hidden`, { is_hidden: !product.is_hidden }, (updated) =>
    updated.is_hidden
      ? `„${updated.name}“ ist jetzt ausgeblendet. Kunden sehen es nicht mehr.`
      : `„${updated.name}“ ist wieder im Katalog sichtbar.`,
  );
}

/**
 * Schickt eine Änderung an ein Produkt, ersetzt den Eintrag durch die Antwort und zeigt eine Meldung.
 * @param {import("./modules/product-admin.js").ManagedProduct} product das Produkt vor der Änderung
 * @param {string} path Pfad der Schnittstelle, z. B. "/products/3/hidden"
 * @param {object} body Feld, das geändert wird
 * @param {(updated: object) => string} describe erzeugt die Erfolgsmeldung aus der Antwort
 */
async function updateProduct(product, path, body, describe) {
  pendingIds.add(product.id);
  showMessage(null);
  renderList();
  try {
    const updated = await requestJson(path, { method: "PUT", body });
    products = products.map((entry) => (entry.id === updated.id ? updated : entry));
    showMessage(describe(updated), "success");
  } catch (error) {
    if (error.status === 401 || error.status === 403) {
      showAccessProblem(error);
    } else {
      showMessage(error.message, "error"); // z. B. "Dieses Produkt gibt es nicht."
    }
  } finally {
    pendingIds.delete(product.id);
    renderList();
  }
}

/**
 * Zeigt eine Meldung unter den Filtern oder blendet sie aus.
 * @param {string|null} text Meldung, null = ausblenden
 * @param {"error"|"success"} [type="error"]
 */
function showMessage(text, type = "error") {
  messageBox.hidden = !text;
  messageBox.textContent = text ?? "";
  messageBox.className = type === "success" ? "alert alert-success" : "alert alert-error";
}
