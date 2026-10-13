/*
 * LaserFlow – layout.js (gemeinsames Verhalten für JEDE Seite)
 *
 * 1. Kopfbereich beim Scrollen verkleinern
 * 2. Benutzermenü (angemeldet / nicht angemeldet)
 * 3. Elemente mit der Klasse "reveal" beim Scrollen einblenden
 *
 * Voraussetzung: Die Seite enthält Kopfbereich und Benutzermenü aus vorlage.html.
 * Gemeinsame Datei: Änderungen nur nach Absprache im Team.
 */

/* ---------- 1. Kopfbereich beim Scrollen ---------- */
const header = document.getElementById("header");

function updateHeader() {
  header.classList.toggle("is-scrolled", window.scrollY > 20);
}

window.addEventListener("scroll", updateHeader);
updateHeader();

/* ---------- 2. Benutzermenü ----------
 * Ob jemand angemeldet ist, weiß später das Backend (FastAPI).
 * Bis dahin simulieren wir es: seite.html?angemeldet=1 zeigt die Ansicht für Angemeldete.
 * Die Links (#) bekommen ihre echten Ziele mit den Stories für Login, Registrierung und Konto.
 */
const params = new URLSearchParams(window.location.search);
const isLoggedIn = params.get("angemeldet") === "1";
const userName = "Max Mustermann"; // Platzhalter, kommt später vom Backend

const userButton = document.getElementById("user-button");
const userDropdown = document.getElementById("user-dropdown");

if (isLoggedIn) {
  userDropdown.innerHTML = `
    <div class="dropdown-head">Angemeldet als <strong>${userName}</strong></div>
    <a href="#" role="menuitem">Mein Konto</a>
    <a href="#" role="menuitem">Meine Bestellungen</a>
    <a href="#" role="menuitem">Persönliche Daten</a>
    <div class="dropdown-divider"></div>
    <a href="#" role="menuitem">Abmelden</a>
  `;
} else {
  userDropdown.innerHTML = `
    <div class="dropdown-head">Willkommen bei <strong>LaserFlow</strong></div>
    <a href="#" class="dropdown-primary" role="menuitem">Anmelden</a>
    <a href="#" role="menuitem">Neu hier? Registrieren</a>
  `;
}

function setMenuOpen(open) {
  userDropdown.classList.toggle("is-open", open);
  userButton.setAttribute("aria-expanded", String(open));
}

// Klick auf das Icon öffnet bzw. schließt das Menü
userButton.addEventListener("click", (event) => {
  event.stopPropagation();
  setMenuOpen(!userDropdown.classList.contains("is-open"));
});

// Klick irgendwo anders oder Escape schließt das Menü
document.addEventListener("click", (event) => {
  if (!userDropdown.contains(event.target)) {
    setMenuOpen(false);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    setMenuOpen(false);
  }
});

/* ---------- 3. Elemente beim Scrollen einblenden ----------
 * Der IntersectionObserver meldet, sobald ein Element in den sichtbaren Bereich kommt.
 * Dann bekommt es die Klasse "is-visible", und die CSS-Übergänge aus design.css starten.
 * Benutzung im HTML: class="reveal" (optional zusätzlich "reveal-delay", "reveal-delay-2", ...).
 */
const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        revealObserver.unobserve(entry.target); // nur einmal animieren
      }
    });
  },
  { threshold: 0.15 }
);

document.querySelectorAll(".reveal").forEach((element) => revealObserver.observe(element));
