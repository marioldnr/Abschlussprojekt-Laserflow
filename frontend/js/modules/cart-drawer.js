/**
 * LaserFlow – cart-drawer.js (Warenkorb als Seitenleiste)
 *
 * Wie im Wireframe "Warenkorb ansehen und bearbeiten": Ein Klick auf das
 * Warenkorb-Icon im Kopfbereich öffnet rechts eine Leiste mit allen Artikeln,
 * Menge ändern (− / +), Artikel entfernen und Gesamtbetrag.
 *
 * Benutzung in einem Seiten-Skript:
 *   import { initCartDrawer, addToCart } from "./modules/cart-drawer.js";
 *   initCartDrawer();            // einmal pro Seite
 *   addToCart(productId, menge); // legt in den Warenkorb und öffnet die Leiste
 *
 * Die Leiste wird per JavaScript erzeugt. Dadurch muss der Kopfbereich in
 * vorlage.html nicht geändert werden. Seiten ohne dieses Modul zeigen am
 * Warenkorb-Icon weiter "0" (siehe docs/module/katalog.md, Bekannte Grenzen).
 */
import { addItem, countItems, loadCart, removeItem, saveCart, setQuantity, totalCents, MAX_QUANTITY } from "./cart.js";
import { findProduct, formatPrice } from "./products.js";

let cart = [];
let drawer;
let overlay;
let lastFocus = null;

/** Baut die Leiste einmal auf und verbindet das Warenkorb-Icon. */
export function initCartDrawer() {
  cart = loadCart();

  overlay = document.createElement("div");
  overlay.className = "cart-overlay";
  overlay.addEventListener("click", closeCart);

  drawer = document.createElement("aside");
  drawer.className = "cart-drawer";
  drawer.setAttribute("role", "dialog");
  drawer.setAttribute("aria-modal", "true");
  drawer.setAttribute("aria-labelledby", "cart-title");
  drawer.setAttribute("aria-hidden", "true");
  drawer.innerHTML = `
    <div class="cart-head">
      <h2 id="cart-title">Warenkorb</h2>
      <button class="icon-button" type="button" data-cart-close aria-label="Warenkorb schließen">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
      </button>
    </div>
    <ul class="cart-list" data-cart-list></ul>
    <div class="cart-empty" data-cart-empty>
      <p>Dein Warenkorb ist noch leer.</p>
      <a href="katalog.html" class="button button-ghost">Zum Katalog</a>
    </div>
    <div class="cart-foot" data-cart-foot>
      <div class="cart-total"><span>Gesamt</span><strong data-cart-total></strong></div>
      <p class="cart-note">inkl. MwSt., zzgl. Versand</p>
      <button class="button button-block" type="button" aria-disabled="true" title="Bestellung abschließen folgt mit der nächsten Story">Zur Kasse</button>
    </div>
  `;

  document.body.append(overlay, drawer);
  drawer.querySelector("[data-cart-close]").addEventListener("click", closeCart);
  drawer.querySelector("[data-cart-list]").addEventListener("click", handleListClick);

  document.querySelectorAll(".header .cart").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      openCart();
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && drawer.classList.contains("is-open")) closeCart();
  });

  // Warenkorb in einem anderen Tab geändert: hier nachziehen
  window.addEventListener("storage", () => {
    cart = loadCart();
    render();
  });

  render();
}

/**
 * Legt ein Produkt in den Warenkorb, speichert und öffnet die Leiste.
 * @param {number} productId
 * @param {number} [quantity=1]
 */
export function addToCart(productId, quantity = 1) {
  update(addItem(cart, productId, quantity));
  openCart();
  bumpIcon();
}

/** Öffnet die Leiste und setzt den Fokus hinein (Tastaturbedienung). */
export function openCart() {
  lastFocus = document.activeElement;
  overlay.classList.add("is-open");
  drawer.classList.add("is-open");
  drawer.setAttribute("aria-hidden", "false");
  document.body.classList.add("cart-is-open");
  drawer.querySelector("[data-cart-close]").focus();
}

/** Schließt die Leiste und gibt den Fokus zurück. */
export function closeCart() {
  overlay.classList.remove("is-open");
  drawer.classList.remove("is-open");
  drawer.setAttribute("aria-hidden", "true");
  document.body.classList.remove("cart-is-open");
  if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
}

function update(nextCart) {
  cart = nextCart;
  saveCart(cart);
  render();
}

/** Klicks auf −, + und Entfernen (ein Listener für die ganze Liste). */
function handleListClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const productId = Number(button.closest("[data-product-id]").dataset.productId);
  const item = cart.find((entry) => entry.productId === productId);
  if (!item) return;

  if (button.dataset.action === "minus") update(setQuantity(cart, productId, item.quantity - 1));
  if (button.dataset.action === "plus") update(setQuantity(cart, productId, item.quantity + 1));
  if (button.dataset.action === "remove") update(removeItem(cart, productId));
}

/** Zeichnet Liste, Summe und die Zahl am Icon neu. */
function render() {
  const list = drawer.querySelector("[data-cart-list]");
  list.replaceChildren(
    ...cart
      .map((item) => ({ item, product: findProduct(item.productId) }))
      .filter(({ product }) => product)
      .map(({ item, product }) => renderItem(item, product))
  );

  const isEmpty = list.children.length === 0;
  drawer.querySelector("[data-cart-empty]").hidden = !isEmpty;
  drawer.querySelector("[data-cart-foot]").hidden = isEmpty;
  drawer.querySelector("[data-cart-total]").textContent = formatPrice(totalCents(cart, (id) => findProduct(id)));

  const count = countItems(cart);
  document.querySelectorAll(".header .cart-count").forEach((badge) => {
    badge.textContent = String(count);
  });
  document.querySelectorAll(".header .cart").forEach((link) => {
    link.setAttribute("aria-label", `Warenkorb, ${count} Artikel`);
  });
}

/**
 * Eine Zeile im Warenkorb. Texte per textContent, nie per innerHTML,
 * damit später Daten aus dem Backend nicht als HTML ausgeführt werden.
 */
function renderItem(item, product) {
  const li = document.createElement("li");
  li.className = "cart-item";
  li.dataset.productId = String(product.id);
  li.innerHTML = `
    <a class="cart-item-image"><img alt=""></a>
    <div class="cart-item-body">
      <a class="cart-item-name"></a>
      <span class="cart-item-price"></span>
      <div class="cart-item-actions">
        <div class="qty qty-small">
          <button type="button" data-action="minus" aria-label="Menge verringern">−</button>
          <span class="qty-value" aria-live="polite"></span>
          <button type="button" data-action="plus" aria-label="Menge erhöhen">+</button>
        </div>
        <button type="button" class="cart-item-remove" data-action="remove">Entfernen</button>
      </div>
    </div>
    <strong class="cart-item-sum"></strong>
  `;
  const href = `produkt.html?id=${product.id}`;
  li.querySelector(".cart-item-image").href = href;
  li.querySelector("img").src = product.images[0];
  li.querySelector(".cart-item-name").href = href;
  li.querySelector(".cart-item-name").textContent = product.name;
  li.querySelector(".cart-item-price").textContent = `${formatPrice(product.price_cent)} / Stück`;
  li.querySelector(".qty-value").textContent = String(item.quantity);
  li.querySelector(".cart-item-sum").textContent = formatPrice(product.price_cent * item.quantity);
  li.querySelector('[data-action="plus"]').disabled = item.quantity >= MAX_QUANTITY;
  return li;
}

/** Kurzes "Hüpfen" des Warenkorb-Icons als Rückmeldung. */
function bumpIcon() {
  document.querySelectorAll(".header .cart").forEach((link) => {
    link.classList.remove("is-bumped");
    void link.offsetWidth; // Animation neu starten
    link.classList.add("is-bumped");
  });
}
