/**
 * LaserFlow – startseite-produkte.js (Produktkacheln auf der Startseite)
 *
 * Setzt für jedes Produkt eine Kachel mit Foto, Name und Preis in den Abschnitt
 * "Unsere Produkte" ein (vor die Kachel "Alle Produkte") und verbindet das
 * Warenkorb-Icon mit der Warenkorb-Leiste. Ausverkaufte Produkte bekommen wie im
 * Katalog das Schild "Ausverkauft" und ein abgedunkeltes Foto.
 */
import { PRODUCTS, formatPrice, loadProducts } from "./modules/products.js";
import { initCartDrawer } from "./modules/cart-drawer.js";

// Lädt die Produkte vom Backend. Gelingt das nicht, bleiben die Kacheln einfach weg.
try {
  await loadProducts();
} catch {
  // Keine Kacheln: die Startseite funktioniert trotzdem (Link "Alle Produkte" führt in den Katalog).
}

initCartDrawer();

const container = document.getElementById("home-products");
const moreTile = container.querySelector(".tile-more");
const delays = ["", " reveal-delay", " reveal-delay-2"];

PRODUCTS.slice(0, 3).forEach((product, index) => {
  const tile = document.createElement("a");
  tile.className = `tile reveal is-visible${delays[index] ?? ""}${product.is_sold_out ? " is-sold-out" : ""}`;
  tile.href = `produkt.html?id=${product.id}`;
  tile.innerHTML = `
    <div class="tile-image"><img loading="lazy" alt=""></div>
    <span class="product-badge" hidden>Ausverkauft</span>
    <div class="tile-body">
      <h3></h3>
      <span class="tile-price"></span>
      <span class="tile-cta">Details ansehen →</span>
    </div>
  `;
  tile.querySelector("img").src = product.images[0];
  tile.querySelector("img").alt = `Produktfoto: ${product.name}`;
  tile.querySelector("h3").textContent = product.name;
  tile.querySelector(".tile-price").textContent = formatPrice(product.price_cent);
  tile.querySelector(".product-badge").hidden = !product.is_sold_out;
  container.insertBefore(tile, moreTile);
});
