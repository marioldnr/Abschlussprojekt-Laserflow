/**
 * LaserFlow – katalog.js (Seite "Produktkatalog anzeigen")
 *
 * Zeigt alle Produkte als Kacheln. Oben: Suche, Kategorie-Filter, Sortierung.
 * Klick auf eine Kachel öffnet produkt.html?id=<id>.
 * Ausverkaufte Produkte bekommen ein Schild "Ausverkauft" (Use Case
 * "Ausverkauft-Kennzeichnung anzeigen").
 */
import { PRODUCTS, filterProducts, formatPrice, listCategories } from "./modules/products.js";
import { initCartDrawer } from "./modules/cart-drawer.js";

initCartDrawer();

const grid = document.getElementById("product-grid");
const search = document.getElementById("product-search");
const sort = document.getElementById("product-sort");
const chips = document.getElementById("category-chips");
const resultInfo = document.getElementById("result-info");

const state = { query: "", category: "", sort: "empfohlen" };

// Kategorie-Knöpfe: "Alle" + eine pro Kategorie
for (const category of ["", ...listCategories()]) {
  const chip = document.createElement("button");
  chip.type = "button";
  chip.className = "chip";
  chip.textContent = category || "Alle";
  chip.dataset.category = category;
  chip.setAttribute("aria-pressed", String(category === ""));
  chips.append(chip);
}

chips.addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  state.category = chip.dataset.category;
  chips.querySelectorAll(".chip").forEach((element) => {
    element.setAttribute("aria-pressed", String(element === chip));
  });
  render();
});

search.addEventListener("input", () => {
  state.query = search.value;
  render();
});

sort.addEventListener("change", () => {
  state.sort = sort.value;
  render();
});

/** Baut eine Produktkachel. Texte per textContent (sicher auch für Backend-Daten). */
function renderCard(product, index) {
  const card = document.createElement("a");
  card.className = `product-card reveal is-visible${product.is_sold_out ? " is-sold-out" : ""}`;
  card.href = `produkt.html?id=${product.id}`;
  card.style.setProperty("--delay", `${index * 80}ms`);
  card.innerHTML = `
    <div class="product-card-image">
      <img loading="lazy" alt="">
      <span class="product-badge" hidden>Ausverkauft</span>
    </div>
    <div class="product-card-body">
      <p class="product-card-category"></p>
      <h3></h3>
      <p class="product-card-text"></p>
      <div class="product-card-foot">
        <span class="product-card-price"></span>
        <span class="tile-cta">Details ansehen →</span>
      </div>
    </div>
  `;
  const image = card.querySelector("img");
  image.src = product.images[0];
  image.alt = `Produktfoto: ${product.name}`;
  card.querySelector(".product-badge").hidden = !product.is_sold_out;
  card.querySelector(".product-card-category").textContent = product.category;
  card.querySelector("h3").textContent = product.name;
  card.querySelector(".product-card-text").textContent = product.short_description;
  card.querySelector(".product-card-price").textContent = formatPrice(product.price_cent);
  return card;
}

function render() {
  const products = filterProducts(PRODUCTS, state);
  grid.replaceChildren(...products.map(renderCard));
  resultInfo.textContent =
    products.length === 0
      ? "Keine Produkte gefunden. Versuch einen anderen Suchbegriff."
      : `${products.length} ${products.length === 1 ? "Produkt" : "Produkte"}`;
}

render();
