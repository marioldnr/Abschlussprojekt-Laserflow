/**
 * LaserFlow – produkt.js (Seite "Produktdetails anzeigen")
 *
 * Liest die Produkt-ID aus der Adresse (produkt.html?id=2) und zeigt:
 * Bildergalerie (Pfeile, Punkte, Vorschaubilder, Wischen auf dem Handy),
 * Name, Preis, Beschreibung, Maße/Material und "In den Warenkorb".
 * Unbekannte ID → Hinweis mit Link zum Katalog. Fehler beim Laden der Produkte → eigener Hinweis.
 * Produkte mit eigenem Bild (has_customer_image) zeigen "Bild hochladen" statt "In den Warenkorb";
 * der Upload folgt mit US04.
 */
import { PRODUCTS, findProduct, formatDimensions, formatPrice, loadProducts } from "./modules/products.js";
import { initCartDrawer, addToCart } from "./modules/cart-drawer.js";
import { MAX_QUANTITY } from "./modules/cart.js";

// Produkte vom Backend laden, bevor die Adresse ausgewertet wird.
let loadError = false;
try {
  await loadProducts();
} catch {
  loadError = true;
}

initCartDrawer();

const params = new URLSearchParams(window.location.search);
const product = findProduct(params.get("id"));

const view = document.getElementById("product-view");
const notFound = document.getElementById("product-not-found");

if (loadError) {
  view.hidden = true;
  notFound.hidden = false;
  notFound.querySelector("h2").textContent = "Das Produkt lässt sich gerade nicht anzeigen.";
  notFound.querySelector("p:not(.eyebrow)").textContent =
    "Die Produkte konnten nicht geladen werden. Bitte später erneut versuchen.";
} else if (!product) {
  view.hidden = true;
  notFound.hidden = false;
} else {
  showProduct(product);
  showRelated(product);
}

/** Füllt die Seite mit den Daten des Produkts. */
function showProduct(product) {
  document.title = `${product.name} – LaserFlow`;
  document.getElementById("crumb-name").textContent = product.name;
  document.getElementById("product-category").textContent = product.category;
  document.getElementById("product-name").textContent = product.name;
  document.getElementById("product-short").textContent = product.short_description;
  document.getElementById("product-price").textContent = formatPrice(product.price_cent);
  document.getElementById("product-description").textContent = product.long_description;
  document.getElementById("product-dimensions").textContent = formatDimensions(product);
  document.getElementById("product-material").textContent = product.material;

  setupGallery(product);
  setupBuyBox(product);
}

/* ---------- Galerie ---------- */

function setupGallery(product) {
  const mainImage = document.getElementById("gallery-image");
  const dots = document.getElementById("gallery-dots");
  const thumbs = document.getElementById("gallery-thumbs");
  const prev = document.getElementById("gallery-prev");
  const next = document.getElementById("gallery-next");
  const stage = document.getElementById("gallery-stage");
  const images = product.images;
  let current = 0;

  images.forEach((src, index) => {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.className = "gallery-dot";
    dot.setAttribute("aria-label", `Bild ${index + 1} von ${images.length}`);
    dot.addEventListener("click", () => show(index));
    dots.append(dot);

    const thumb = document.createElement("button");
    thumb.type = "button";
    thumb.className = "gallery-thumb";
    thumb.setAttribute("aria-label", `Bild ${index + 1} anzeigen`);
    const image = document.createElement("img");
    image.src = src;
    image.alt = "";
    thumb.append(image);
    thumb.addEventListener("click", () => show(index));
    thumbs.append(thumb);
  });

  const single = images.length < 2;
  prev.hidden = single;
  next.hidden = single;
  dots.hidden = single;
  thumbs.hidden = single;

  prev.addEventListener("click", () => show(current - 1));
  next.addEventListener("click", () => show(current + 1));

  // Pfeiltasten, wenn die Galerie den Fokus hat
  stage.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") show(current - 1);
    if (event.key === "ArrowRight") show(current + 1);
  });

  // Wischen auf dem Handy
  let touchStartX = null;
  stage.addEventListener("touchstart", (event) => { touchStartX = event.touches[0].clientX; }, { passive: true });
  stage.addEventListener("touchend", (event) => {
    if (touchStartX === null) return;
    const delta = event.changedTouches[0].clientX - touchStartX;
    if (Math.abs(delta) > 40) show(current + (delta < 0 ? 1 : -1));
    touchStartX = null;
  });

  function show(index) {
    current = (index + images.length) % images.length; // am Ende wieder von vorn
    mainImage.classList.remove("is-shown");
    mainImage.src = images[current];
    mainImage.alt = `${product.name}, Ansicht ${current + 1} von ${images.length}`;
    requestAnimationFrame(() => mainImage.classList.add("is-shown"));
    [...dots.children].forEach((dot, i) => dot.setAttribute("aria-current", String(i === current)));
    [...thumbs.children].forEach((thumb, i) => thumb.setAttribute("aria-current", String(i === current)));
  }

  show(0);
}

/* ---------- Menge und "In den Warenkorb" ---------- */

function setupBuyBox(product) {
  const value = document.getElementById("qty-value");
  const minus = document.getElementById("qty-minus");
  const plus = document.getElementById("qty-plus");
  const addButton = document.getElementById("add-to-cart");
  const soldOut = document.getElementById("sold-out-note");
  let quantity = 1;

  // Hinweis unter dem Kaufbereich, nur für den Upload-Platzhalter (kein alert)
  const uploadNote = document.createElement("p");
  uploadNote.className = "product-price-note";
  uploadNote.setAttribute("role", "status");
  uploadNote.hidden = true;
  addButton.parentElement.insertAdjacentElement("afterend", uploadNote);

  function update() {
    value.textContent = String(quantity);
    minus.disabled = quantity <= 1;
    plus.disabled = quantity >= MAX_QUANTITY;
  }

  minus.addEventListener("click", () => { quantity = Math.max(1, quantity - 1); update(); });
  plus.addEventListener("click", () => { quantity = Math.min(MAX_QUANTITY, quantity + 1); update(); });

  if (product.is_sold_out) {
    addButton.disabled = true;
    addButton.textContent = "Ausverkauft";
    soldOut.hidden = false;
  } else if (product.has_customer_image) {
    addButton.textContent = "Bild hochladen";
  }

  addButton.addEventListener("click", () => {
    // Produkte mit eigenem Bild kommen erst mit US04 in den Warenkorb; bis dahin nur ein Hinweis.
    if (product.has_customer_image && !product.is_sold_out) {
      uploadNote.textContent = "Der Bild-Upload folgt in Kürze (US04).";
      uploadNote.hidden = false;
      return;
    }
    addToCart(product.id, quantity);
    quantity = 1;
    update();
  });

  update();
}

/* ---------- Weitere Produkte ---------- */

function showRelated(product) {
  const list = document.getElementById("related-list");
  PRODUCTS.filter((other) => other.id !== product.id).forEach((other) => {
    const link = document.createElement("a");
    link.className = "tile";
    link.href = `produkt.html?id=${other.id}`;
    link.innerHTML = `
      <div class="tile-image"><img alt=""></div>
      <div class="tile-body"><h3></h3><span class="tile-price"></span></div>
    `;
    link.querySelector("img").src = other.images[0];
    link.querySelector("img").alt = `Produktfoto: ${other.name}`;
    link.querySelector("h3").textContent = other.name;
    link.querySelector(".tile-price").textContent = formatPrice(other.price_cent);
    list.append(link);
  });
}
