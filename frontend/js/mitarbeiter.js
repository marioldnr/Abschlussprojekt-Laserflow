/**
 * LaserFlow – Seite "Mitarbeiter verwalten" (mitarbeiter.html, US15)
 *
 * Ablauf:
 * 1. Beim Laden die Mitarbeiterliste holen (GET /api/admin/employees).
 *    401 = niemand angemeldet → Hinweis mit Link zur Anmeldung.
 *    403 = angemeldet, aber kein Admin → Hinweis, die Maske bleibt verborgen.
 * 2. Anlegen: Felder im Browser prüfen, dann POST /api/admin/employees.
 * 3. Bearbeiten: Stift in der Liste → Formular wird mit den Daten gefüllt und wechselt in den
 *    Bearbeiten-Modus. Speichern = PUT /api/admin/employees/<id>. Passwort leer = bleibt.
 *    Deaktivierte Accounts haben keinen Stift und lassen sich nicht bearbeiten.
 * 4. Deaktivieren (im Bearbeiten-Modus): eigener Button, schickt PUT mit is_active false. Das ist
 *    endgültig (PO-Entscheidung 20.10.2026), es gibt kein Reaktivieren. Deaktivierte Accounts
 *    bleiben ausgegraut in der Liste und können sich nicht anmelden. Echtes Löschen gibt es
 *    bewusst nicht (Löschen nur per Flag).
 *
 * Wer Admin ist, prüft das Backend bei jeder Anfrage. Das Verstecken der Maske hier ist
 * nur Komfort, kein Schutz.
 */

import { requestJson } from "./modules/api-client.js";
import { fieldErrorsFromApi } from "./modules/auth-api.js";
import { email, personName, required, strongPassword } from "./modules/validation.js";
import {
  enableLiveValidation,
  initPasswordToggles,
  setBusy,
  setFieldError,
  showAlert,
  showErrors,
  validateForm,
} from "./modules/form.js";
import { loginUrlFor } from "./modules/navigation.js";

/** Pfad der Schnittstelle (ab /api, siehe api-client.js). */
const EMPLOYEES_PATH = "/admin/employees";

/** Anzeigenamen der Rollen. */
const ROLE_LABELS = { employee: "Mitarbeiter", admin: "Admin" };

/** ID des Mitarbeiters, der gerade bearbeitet wird (null = Modus "anlegen"). */
let editingId = null;

/** Zuletzt geladene Liste, damit der Stift die Daten ohne neue Anfrage einsetzen kann. */
let employees = [];

/** Aktiver Filter der Liste: "all", "admin", "employee" oder "inactive". */
let activeFilter = "all";

/**
 * Passwort: beim Anlegen Pflicht, beim Bearbeiten darf es leer bleiben (= unverändert).
 * @param {string} value
 * @returns {string|null}
 */
function passwordRule(value) {
  if (editingId !== null && String(value) === "") {
    return null;
  }
  return strongPassword(value);
}

/** Prüfregeln pro Feld (Namen wie die name-Attribute im HTML). */
const SCHEMA = {
  firstName: [required, personName],
  lastName: [required, personName],
  email: [required, email],
  password: [passwordRule],
  role: [required],
};

const form = document.getElementById("employee-form");
const editor = document.getElementById("staff-editor");
const card = document.getElementById("staff-card");
const list = document.getElementById("staff-list");
const items = document.getElementById("staff-items");
const emptyHint = document.getElementById("staff-empty");
const searchInput = document.getElementById("staff-search");
const filterButtons = document.querySelectorAll("[data-filter]");
const statTotal = document.getElementById("stat-total");
const statAdmins = document.getElementById("stat-admins");
const statInactive = document.getElementById("stat-inactive");
const accessAlert = document.getElementById("staff-access");
const formTitle = document.getElementById("form-title");
const formIntro = document.getElementById("form-intro");
const passwordHint = document.getElementById("password-hint");
const statusRow = document.getElementById("status-row");
const statusText = document.getElementById("status-text");
const toggleButton = document.getElementById("toggle-active");
const submitButton = document.getElementById("submit-button");
const cancelButton = document.getElementById("cancel-edit");

initPasswordToggles(form);
enableLiveValidation(form, SCHEMA);
cancelButton.addEventListener("click", () => startCreateMode());
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
toggleButton.addEventListener("click", onDeactivate);
form.addEventListener("submit", onSubmit);

loadEmployees();

/**
 * Holt die Liste vom Backend und zeigt Maske und Liste an.
 * Bei fehlender Berechtigung erscheint stattdessen ein Hinweis.
 */
async function loadEmployees() {
  try {
    employees = await requestJson(EMPLOYEES_PATH);
  } catch (error) {
    showAccessProblem(error);
    return;
  }
  accessAlert.hidden = true;
  editor.hidden = false;
  list.hidden = false;
  renderList();
}

/**
 * Zeigt, warum die Seite nicht benutzt werden kann.
 * @param {import("./modules/api-client.js").ApiError} error
 */
function showAccessProblem(error) {
  editor.hidden = true;
  list.hidden = true;
  accessAlert.hidden = false;
  accessAlert.textContent = "";

  if (error.status === 401) {
    // Link per DOM bauen (nicht innerHTML), damit nie fremder Text als HTML ausgeführt wird.
    accessAlert.append("Bitte melde dich als Admin an. ");
    const link = document.createElement("a");
    link.className = "text-link";
    link.href = loginUrlFor("mitarbeiter.html");
    link.textContent = "Zur Anmeldung";
    accessAlert.append(link);
  } else {
    accessAlert.textContent = error.message; // 403: "Diese Seite ist nur für Admins." oder Server nicht erreichbar
  }
}

/** Baut die Liste der Mitarbeiter neu auf. */
function renderList() {
  statTotal.textContent = employees.length;
  statAdmins.textContent = employees.filter((e) => e.role === "admin" && e.is_active).length;
  statInactive.textContent = employees.filter((e) => !e.is_active).length;

  const visible = filterEmployees(employees, searchInput.value, activeFilter);
  items.replaceChildren(...visible.map(renderItem));

  emptyHint.hidden = visible.length > 0;
  emptyHint.textContent = employees.length === 0 ? "Noch keine Mitarbeiter angelegt." : "Keine Treffer für diese Suche.";
}

/**
 * Filtert die Liste nach Suchtext (Name oder E-Mail) und Filter-Knopf.
 * @param {Array<{ email: string, first_name: string|null, last_name: string|null, role: string, is_active: boolean }>} list
 * @param {string} query Suchtext, Groß-/Kleinschreibung egal
 * @param {"all"|"admin"|"employee"|"inactive"} filter
 * @returns {Array} die passenden Einträge
 */
function filterEmployees(list, query, filter) {
  const text = query.trim().toLowerCase();
  return list.filter((employee) => {
    if (filter === "admin" && !(employee.role === "admin" && employee.is_active)) return false;
    if (filter === "employee" && !(employee.role === "employee" && employee.is_active)) return false;
    if (filter === "inactive" && employee.is_active) return false;
    if (!text) return true;
    return `${fullName(employee)} ${employee.email}`.toLowerCase().includes(text);
  });
}

/**
 * Initialen für das runde Kürzel, z. B. "MM" für Max Muster (sonst erster Buchstabe der E-Mail).
 * @param {{ first_name: string|null, last_name: string|null, email: string }} employee
 * @returns {string}
 */
function initials(employee) {
  const letters = [employee.first_name, employee.last_name].filter(Boolean).map((part) => part.trim()[0]);
  return (letters.join("") || employee.email[0] || "?").toUpperCase();
}

/**
 * Eine Zeile der Liste: Initialen, Name, E-Mail, Rolle und Stift zum Bearbeiten.
 * Texte immer per textContent, damit eingegebene Namen nie als HTML ausgeführt werden.
 * @param {{ id: number, email: string, first_name: string|null, last_name: string|null, role: string, is_active: boolean }} employee
 * @returns {HTMLLIElement}
 */
function renderItem(employee) {
  const item = document.createElement("li");
  item.className = "staff-item";
  item.classList.toggle("is-inactive", !employee.is_active);
  item.classList.toggle("is-selected", employee.id === editingId);

  const avatar = document.createElement("span");
  avatar.className = "staff-avatar";
  avatar.classList.toggle("is-admin", employee.role === "admin" && employee.is_active);
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = initials(employee);

  const text = document.createElement("div");
  const name = document.createElement("p");
  name.className = "staff-name";
  name.textContent = fullName(employee);
  const mail = document.createElement("p");
  mail.className = "staff-mail";
  mail.textContent = employee.email;
  text.append(name, mail);

  const role = document.createElement("span");
  role.className = "staff-role";
  if (employee.is_active) {
    role.classList.toggle("is-admin", employee.role === "admin");
    role.textContent = ROLE_LABELS[employee.role] ?? employee.role;
  } else {
    role.classList.add("is-inactive");
    role.textContent = "Deaktiviert";
  }

  item.append(avatar, text, role);

  // Deaktivierte Accounts bekommen keinen Stift: Deaktivieren ist endgültig, also nicht mehr bearbeitbar.
  // Ohne Stift bleibt die Rollen-Spalte trotzdem auf derselben Position wie bei aktiven Zeilen.
  if (employee.is_active) {
    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "icon-button";
    edit.setAttribute("aria-label", `${fullName(employee)} bearbeiten`);
    edit.innerHTML =
      '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M14 6l4 4"/></svg>';
    edit.addEventListener("click", () => startEditMode(employee));
    item.append(edit);
  }
  return item;
}

/**
 * "Vorname Nachname", sonst die E-Mail.
 * @param {{ first_name: string|null, last_name: string|null, email: string }} employee
 * @returns {string}
 */
function fullName(employee) {
  return [employee.first_name, employee.last_name].filter(Boolean).join(" ") || employee.email;
}

/** Formular leeren und auf "anlegen" stellen. */
function startCreateMode() {
  editingId = null;
  form.reset();
  clearMessages();
  formTitle.textContent = "Mitarbeiter anlegen";
  formIntro.textContent = "Lege einen Account für einen Mitarbeiter oder Admin an.";
  passwordHint.textContent = "Startpasswort: mindestens 8 Zeichen, ein Buchstabe und eine Ziffer.";
  form.elements.namedItem("password").required = true;
  statusRow.hidden = true;
  submitButton.textContent = "Mitarbeiter anlegen";
  submitButton.dataset.label = submitButton.textContent; // setBusy merkt sich sonst die alte Beschriftung
  cancelButton.hidden = true;
  card.classList.remove("is-editing");
  renderList();
}

/**
 * Formular mit den Daten eines Mitarbeiters füllen und auf "bearbeiten" stellen.
 * @param {{ id: number, email: string, first_name: string|null, last_name: string|null, role: string, is_active: boolean }} employee
 */
function startEditMode(employee) {
  editingId = employee.id;
  clearMessages();
  form.elements.namedItem("firstName").value = employee.first_name ?? "";
  form.elements.namedItem("lastName").value = employee.last_name ?? "";
  form.elements.namedItem("email").value = employee.email;
  form.elements.namedItem("password").value = "";
  form.elements.namedItem("password").required = false;
  form.elements.namedItem("role").value = employee.role;

  formTitle.textContent = "Mitarbeiter bearbeiten";
  formIntro.textContent = fullName(employee);
  passwordHint.textContent = "Leer lassen, wenn das Passwort gleich bleiben soll.";
  statusRow.hidden = false;
  statusText.textContent = "Deaktivieren ist endgültig: Der Account kann sich danach nicht mehr anmelden und lässt sich nicht wieder aktivieren.";
  submitButton.textContent = "Änderungen speichern";
  submitButton.dataset.label = submitButton.textContent;
  cancelButton.hidden = false;
  card.classList.add("is-editing");
  renderList();
  editor.scrollIntoView({ behavior: "smooth", block: "start" });
  form.elements.namedItem("firstName").focus({ preventScroll: true });
}

/** Alle Fehler und Hinweise im Formular entfernen. */
function clearMessages() {
  showErrors(form, {}, SCHEMA);
  showAlert(form, null);
}

/**
 * Absenden: prüfen, an das Backend schicken, Liste aktualisieren.
 * @param {SubmitEvent} event
 */
async function onSubmit(event) {
  event.preventDefault();
  showAlert(form, null);

  const { valid, values } = validateForm(form, SCHEMA);
  if (!valid) return;

  const body = {
    email: values.email.trim(),
    first_name: values.firstName.trim(),
    last_name: values.lastName.trim(),
    role: values.role,
  };

  setBusy(form, true);
  try {
    if (editingId === null) {
      const created = await requestJson(EMPLOYEES_PATH, {
        method: "POST",
        body: { ...body, password: values.password },
      });
      employees = await requestJson(EMPLOYEES_PATH);
      startCreateMode();
      showAlert(form, `${fullName(created)} wurde angelegt.`, "success");
    } else {
      const updated = await requestJson(`${EMPLOYEES_PATH}/${editingId}`, {
        method: "PUT",
        body: { ...body, is_active: currentEmployee().is_active, password: values.password || null },
      });
      employees = await requestJson(EMPLOYEES_PATH);
      startCreateMode();
      showAlert(form, `Änderungen an ${fullName(updated)} gespeichert.`, "success");
    }
  } catch (error) {
    handleSaveError(error);
  } finally {
    setBusy(form, false);
  }
}

/**
 * Fehler beim Speichern am passenden Feld oder über dem Formular anzeigen.
 * @param {import("./modules/api-client.js").ApiError} error
 */
function handleSaveError(error) {
  if (error.status === 401 || error.status === 403) {
    showAccessProblem(error);
    return;
  }
  if (error.status === 409) {
    setFieldError(form, "email", error.message); // E-Mail schon vergeben
    form.elements.namedItem("email").focus();
    return;
  }
  const fieldErrors = fieldErrorsFromApi(error);
  if (Object.keys(fieldErrors).length > 0) {
    for (const [name, message] of Object.entries(fieldErrors)) {
      setFieldError(form, name, message);
    }
    form.querySelector('[aria-invalid="true"]')?.focus();
    return;
  }
  showAlert(form, error.message, "error"); // z. B. "Es muss mindestens ein aktiver Admin bleiben."
}

/**
 * Der Mitarbeiter, der gerade bearbeitet wird (aus der zuletzt geladenen Liste).
 * @returns {{ id: number, email: string, first_name: string|null, last_name: string|null, role: string, is_active: boolean }}
 */
function currentEmployee() {
  return employees.find((entry) => entry.id === editingId);
}

/**
 * Deaktiviert den bearbeiteten Account endgültig (mit Rückfrage). Es gibt kein Reaktivieren.
 * Geschickt werden die gespeicherten Daten, nicht die Felder im Formular: Ungespeicherte
 * Änderungen in der Maske sollen dabei nicht nebenbei mitgespeichert werden.
 */
async function onDeactivate() {
  const employee = currentEmployee();
  if (!employee) return;
  const name = fullName(employee);

  const confirmed = window.confirm(
    `Account von ${name} endgültig deaktivieren?\n\n${name} kann sich danach nicht mehr anmelden. Das lässt sich nicht rückgängig machen: Der Account kann nicht wieder aktiviert werden.`,
  );
  if (!confirmed) return;

  showAlert(form, null);
  toggleButton.disabled = true;
  try {
    await requestJson(`${EMPLOYEES_PATH}/${employee.id}`, {
      method: "PUT",
      body: {
        email: employee.email,
        first_name: employee.first_name ?? "",
        last_name: employee.last_name ?? "",
        role: employee.role,
        is_active: false,
        password: null,
      },
    });
    employees = await requestJson(EMPLOYEES_PATH);
    startCreateMode();
    showAlert(form, `Der Account von ${name} wurde deaktiviert.`, "success");
  } catch (error) {
    handleSaveError(error); // z. B. "Es muss mindestens ein aktiver Admin bleiben."
  } finally {
    toggleButton.disabled = false;
  }
}
