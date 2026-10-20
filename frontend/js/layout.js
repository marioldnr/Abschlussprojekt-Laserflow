/*
 * LaserFlow – layout.js (gemeinsames Verhalten für JEDE Seite)
 *
 * 0. Favicon sicherstellen (Pflicht auf jeder Seite)
 * 1. Kopfbereich beim Scrollen verkleinern
 * 2. Benutzermenü (angemeldet / nicht angemeldet)
 * 3. Elemente mit der Klasse "reveal" beim Scrollen einblenden
 *
 * Voraussetzung: Die Seite enthält Kopfbereich und Benutzermenü aus vorlage.html.
 * Gemeinsame Datei: Änderungen nur nach Absprache im Team.
 */

/* ---------- 0. Favicon sicherstellen ----------
 * Eigentlich steht das Favicon schon im <head> jeder Seite (siehe vorlage.html).
 * Fehlt es doch einmal, ergänzt layout.js es automatisch. So zeigt jede Seite,
 * die layout.js einbindet, das LaserFlow-Icon in der Tableiste.
 * Der Pfad wird relativ zu dieser Skriptdatei berechnet, damit es auch in Unterordnern klappt.
 */
const scriptUrl = document.currentScript ? document.currentScript.src : window.location.href;

if (!document.querySelector('link[rel="icon"]')) {
  const icons = [
    { rel: "icon", type: "image/svg+xml", file: "favicon.svg" },
    { rel: "icon", type: "image/png", file: "favicon-32.png" },
    { rel: "apple-touch-icon", file: "apple-touch-icon.png" },
  ];
  icons.forEach((icon) => {
    const link = document.createElement("link");
    link.rel = icon.rel;
    if (icon.type) link.type = icon.type;
    link.href = new URL(`../img/logo/${icon.file}`, scriptUrl).href;
    document.head.appendChild(link);
  });
}

/* ---------- 1. Kopfbereich beim Scrollen ---------- */
const header = document.getElementById("header");

function updateHeader() {
  header.classList.toggle("is-scrolled", window.scrollY > 20);
}

window.addEventListener("scroll", updateHeader);
updateHeader();

/* ---------- 2. Benutzermenü ----------
 * Ob jemand angemeldet ist, fragt die Seite beim Backend nach (GET /api/auth/me).
 * Bis die Antwort da ist (oder wenn das Backend nicht läuft, z. B. über Live Server),
 * zeigt das Menü die Ansicht für Gäste.
 * Zum Gestalten ohne Backend gibt es weiter die Simulation: seite.html?angemeldet=1.
 * "Anmelden" und "Registrieren" führen auf anmelden.html bzw. registrieren.html, "Abmelden"
 * ruft POST /api/auth/logout auf. Die übrigen Links für Angemeldete (#) bekommen ihre
 * Ziele mit den Stories für Konto und Bestellhistorie.
 */
const params = new URLSearchParams(window.location.search);

// Link zur Anmeldeseite merkt sich die aktuelle Seite (?weiter=...), damit der Kunde
// nach dem Login dorthin zurückkehrt (Use Case "Anmelden": zum gewählten Produkt zurückkehren).
// Auf den Anmelde-, Registrierungs- und Bestätigungsseiten selbst wäre das sinnlos, dort zeigt der Link einfach auf die Anmeldung.
const currentPage = window.location.pathname.split("/").pop() || "index.html";
const isAuthPage = ["anmelden.html", "registrieren.html", "bestaetigen.html"].includes(currentPage);
const loginHref = isAuthPage
  ? "anmelden.html"
  : `anmelden.html?weiter=${encodeURIComponent(currentPage + window.location.search + window.location.hash)}`;

const userButton = document.getElementById("user-button");
const userDropdown = document.getElementById("user-dropdown");

/**
 * Füllt das Benutzermenü.
 * @param {{ first_name?: string, last_name?: string, email?: string } | null} user angemeldeter Kunde oder null
 */
function renderUserMenu(user) {
  if (!user) {
    userDropdown.innerHTML = `
      <div class="dropdown-head">Willkommen bei <strong>LaserFlow</strong></div>
      <a href="${loginHref}" class="dropdown-primary" role="menuitem">Anmelden</a>
      <a href="registrieren.html" role="menuitem">Neu hier? Registrieren</a>
    `;
    return;
  }

  userDropdown.innerHTML = `
    <div class="dropdown-head">Angemeldet als <strong data-user-name></strong></div>
    <a href="#" role="menuitem">Mein Konto</a>
    <a href="#" role="menuitem">Meine Bestellungen</a>
    <a href="#" role="menuitem">Persönliche Daten</a>
    <div class="dropdown-divider"></div>
    <a href="#" role="menuitem" data-logout>Abmelden</a>
  `;
  // Name per textContent einsetzen (nicht per innerHTML), damit eingegebener Text nie als HTML ausgeführt wird.
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email || "";
  userDropdown.querySelector("[data-user-name]").textContent = name;
  userDropdown.querySelector("[data-logout]").addEventListener("click", logout);
}

/** Abmelden: Sitzung im Backend beenden und zur Startseite. */
async function logout(event) {
  event.preventDefault();
  try {
    await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
  } catch {
    // Backend nicht erreichbar: trotzdem zur Startseite, das Menü zeigt dann den Stand vom Backend.
  }
  window.location.assign("index.html");
}

/** Fragt das Backend, wer angemeldet ist, und aktualisiert das Menü. */
async function loadCurrentUser() {
  try {
    const response = await fetch("/api/auth/me", {
      headers: { Accept: "application/json" },
      credentials: "same-origin", // Sitzungs-Cookie mitschicken
    });
    if (response.ok) {
      renderUserMenu(await response.json());
    }
  } catch {
    // Backend nicht erreichbar (z. B. Live Server): Gast-Ansicht bleibt stehen.
  }
}

if (params.get("angemeldet") === "1") {
  renderUserMenu({ first_name: "Max", last_name: "Mustermann" }); // Simulation zum Gestalten
} else {
  renderUserMenu(null);
  loadCurrentUser();
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
