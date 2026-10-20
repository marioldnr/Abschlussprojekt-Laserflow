/**
 * LaserFlow – Seite "Mein Konto" (konto.html), US10
 *
 * Ablauf:
 * - Beim Laden: Kontodaten holen. Nicht angemeldet → zur Anmeldung (danach zurück hierher).
 * - Profilbild: Datei wählen → prüfen → hochladen → Bild hier und oben im Icon tauschen.
 * - Persönliche Daten, E-Mail, Passwort: Stift-Knopf öffnet das Formular, "Abbrechen" schließt es.
 *   Fehler: Feld rot, Meldung darunter (Prüfung im Browser und noch einmal im Backend).
 * - E-Mail ändern: neue Adresse + Passwort → Code an die neue Adresse → Code eingeben.
 * - Konto löschen: Bestätigungsfenster (<dialog>) mit Passwort + Häkchen → Konto deaktiviert,
 *   Kunde abgemeldet → Startseite. Anonymisiert wird im Backend, sobald alle Bestellungen versendet sind.
 */

import {
  required,
  email,
  strongPassword,
  matchesField,
  personName,
  streetName,
  houseNumber,
  postalCode,
  city,
  verificationCode,
} from "./modules/validation.js";
import {
  validateForm,
  enableLiveValidation,
  initPasswordToggles,
  showAlert,
  setBusy,
  setFieldError,
  focusFirstError,
} from "./modules/form.js";
import { fieldErrorsFromApi } from "./modules/auth-api.js";
import {
  getAccount,
  updateProfile,
  changePassword,
  requestEmailChange,
  confirmEmailChange,
  resendEmailChangeCode,
  cancelEmailChange,
  uploadAvatar,
  removeAvatar,
  deleteAccount,
  checkAvatarFile,
} from "./modules/account-api.js";
import { loginUrlFor } from "./modules/navigation.js";

/** Wie lange der Hinweis nach dem Löschen zu sehen ist, bevor es zur Startseite geht. */
const REDIRECT_DELAY_MS = 3000;

/** Fehler, die zum Code-Feld gehören (falsch, abgelaufen, zu viele Versuche). */
const CODE_ERROR_STATUS = [400, 410, 429];

// ---------- Prüfregeln pro Formular (Feldnamen = name-Attribute im HTML) ----------

const PROFILE_SCHEMA = {
  firstName: [required, personName],
  lastName: [required, personName],
  street: [required, streetName],
  houseNumber: [required, houseNumber],
  postalCode: [required, postalCode],
  city: [required, city],
};

const EMAIL_SCHEMA = {
  newEmail: [required, email],
  password: [required],
};

const EMAIL_CODE_SCHEMA = {
  code: [required, verificationCode],
};

const PASSWORD_SCHEMA = {
  currentPassword: [required],
  newPassword: [required, strongPassword],
  newPasswordConfirm: [required, matchesField("newPassword")],
};

/** Häkchen "Ich möchte mein Konto wirklich löschen" */
const confirmDelete = (checked) => (checked === true ? null : "Bitte bestätige, dass du dein Konto löschen möchtest.");

const DELETE_SCHEMA = {
  password: [required],
  confirm: [confirmDelete],
};

// ---------- Elemente ----------

const pageAlert = document.getElementById("konto-alert");
const avatarForm = document.getElementById("avatar-form");
const avatarInput = document.getElementById("avatar");
const avatarImage = document.querySelector("[data-avatar-image]");
const avatarPlaceholder = document.querySelector("[data-avatar-placeholder]");
const avatarRemoveButton = document.getElementById("avatar-remove");

const profileView = document.getElementById("profile-view");
const profileForm = document.getElementById("profile-form");
const emailForm = document.getElementById("email-form");
const emailCodeForm = document.getElementById("email-code-form");
const passwordForm = document.getElementById("password-form");
const passwordView = document.getElementById("password-view");
const deleteStartButton = document.getElementById("delete-start");
const deleteDialog = document.getElementById("delete-dialog");
const deleteForm = document.getElementById("delete-form");

/** Zuletzt geladene Kontodaten (Antwort von GET /api/account). */
let account = null;

// ---------- Start ----------

init();

async function init() {
  try {
    account = await getAccount();
  } catch (error) {
    if (error.status === 401) {
      // Nicht angemeldet: zur Anmeldung, danach zurück zu "Mein Konto"
      window.location.replace(loginUrlFor("konto.html"));
      return;
    }
    showPageAlert(error.message, "error");
    return;
  }
  render();
  connectAvatar();
  connectProfile();
  connectEmail();
  connectPassword();
  connectDelete();
}

// ---------- Anzeige ----------

/** Füllt die Seite mit den Kontodaten. */
function render() {
  setText("[data-first-name]", account.first_name ?? "");
  setText("[data-created-at]", formatDate(account.created_at));
  setText('[data-view="name"]', `${account.first_name ?? ""} ${account.last_name ?? ""}`.trim());
  setText(
    '[data-view="address"]',
    account.street ? `${account.street} ${account.house_number}\n${account.postal_code} ${account.city}` : "–",
  );
  setText('[data-view="email"]', account.email);
  renderAvatar(account.avatar_url);

  // Offene E-Mail-Änderung (z. B. Seite neu geladen, bevor der Code eingegeben war)
  if (account.pending_email) {
    showEmailCodeStep(account.pending_email);
  }
}

/**
 * Zeigt das Profilbild hier und oben im Benutzer-Icon (layout.js hört auf das Ereignis).
 * @param {string|null} url
 */
function renderAvatar(url) {
  avatarImage.hidden = !url;
  avatarPlaceholder.hidden = Boolean(url);
  avatarRemoveButton.hidden = !url;
  if (url) {
    avatarImage.src = url;
  } else {
    avatarImage.removeAttribute("src");
  }
  window.dispatchEvent(new CustomEvent("laserflow:avatar-changed", { detail: { avatarUrl: url } }));
}

function setText(selector, text) {
  for (const element of document.querySelectorAll(selector)) {
    element.textContent = text;
  }
}

/** "2026-10-20T09:35:03" → "20.10.2026" */
function formatDate(isoText) {
  const date = new Date(isoText);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString("de-DE");
}

/** Hinweis oben auf der Seite (z. B. "Gespeichert"). */
function showPageAlert(message, type = "success") {
  pageAlert.textContent = message ?? "";
  pageAlert.hidden = !message;
  pageAlert.className = `alert alert-${type}`;
}

/**
 * Zeigt Fehler vom Backend an: Feldfehler (422) am Feld, sonst über dem Formular.
 * @param {HTMLFormElement} form
 * @param {import("./modules/api-client.js").ApiError} error
 */
function showServerErrors(form, error) {
  const fieldErrors = error.status === 422 ? fieldErrorsFromApi(error) : {};
  const known = Object.keys(fieldErrors).filter((name) => form.elements.namedItem(name));
  if (known.length === 0) {
    showAlert(form, error.message, "error");
    return;
  }
  for (const name of known) {
    setFieldError(form, name, fieldErrors[name]);
  }
  focusFirstError(form);
}

/**
 * Öffnet bzw. schließt ein Formular. Beim Schließen werden Eingaben und Fehler gelöscht.
 * @param {HTMLFormElement} form
 * @param {boolean} open
 * @param {HTMLElement} [view] Ansicht, die solange ausgeblendet wird
 */
function toggleForm(form, open, view) {
  form.hidden = !open;
  if (view) view.hidden = open;
  if (!open) {
    resetForm(form);
  } else {
    form.querySelector("input")?.focus();
  }
}

/**
 * Leert ein Formular und entfernt alle Fehlermeldungen.
 * @param {HTMLFormElement} form
 */
function resetForm(form) {
  form.reset();
  showAlert(form, null);
  for (const element of form.querySelectorAll("[aria-invalid]")) {
    setFieldError(form, element.name, null);
  }
}

// ---------- Profilbild ----------

function connectAvatar() {
  avatarInput.addEventListener("change", async () => {
    const file = avatarInput.files[0];
    avatarInput.value = ""; // gleiche Datei später erneut wählbar
    if (!file) return;

    const message = checkAvatarFile(file);
    setFieldError(avatarForm, "avatar", message);
    if (message) return;

    try {
      const result = await uploadAvatar(file);
      account.avatar_url = result.avatar_url;
      renderAvatar(result.avatar_url);
      showPageAlert("Dein Profilbild wurde gespeichert.");
    } catch (error) {
      setFieldError(avatarForm, "avatar", fieldErrorsFromApi(error).avatar ?? error.message);
    }
  });

  avatarRemoveButton.addEventListener("click", async () => {
    try {
      await removeAvatar();
      account.avatar_url = null;
      renderAvatar(null);
      showPageAlert("Dein Profilbild wurde entfernt.");
    } catch (error) {
      setFieldError(avatarForm, "avatar", error.message);
    }
  });
}

// ---------- Persönliche Daten ----------

function connectProfile() {
  enableLiveValidation(profileForm, PROFILE_SCHEMA);

  document.getElementById("profile-edit").addEventListener("click", () => {
    toggleForm(profileForm, true, profileView);
    // Formular mit den aktuellen Daten füllen
    const values = {
      firstName: account.first_name,
      lastName: account.last_name,
      street: account.street,
      houseNumber: account.house_number,
      postalCode: account.postal_code,
      city: account.city,
    };
    for (const [name, value] of Object.entries(values)) {
      profileForm.elements.namedItem(name).value = value ?? "";
    }
  });
  profileForm.querySelector("[data-cancel]").addEventListener("click", () => toggleForm(profileForm, false, profileView));

  profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    showAlert(profileForm, null);
    const { valid, values } = validateForm(profileForm, PROFILE_SCHEMA);
    if (!valid) return;

    setBusy(profileForm, true);
    try {
      account = await updateProfile(values);
      render();
      toggleForm(profileForm, false, profileView);
      showPageAlert("Deine persönlichen Daten wurden gespeichert.");
    } catch (error) {
      showServerErrors(profileForm, error);
    } finally {
      setBusy(profileForm, false);
    }
  });
}

// ---------- E-Mail ändern ----------

/** Schritt 2: Code-Eingabe für die neue Adresse anzeigen. */
function showEmailCodeStep(pendingEmail) {
  emailForm.hidden = true;
  emailCodeForm.hidden = false;
  emailCodeForm.querySelector("[data-pending-email]").textContent = pendingEmail;
}

function closeEmailForms() {
  toggleForm(emailForm, false);
  toggleForm(emailCodeForm, false);
}

function connectEmail() {
  enableLiveValidation(emailForm, EMAIL_SCHEMA);
  enableLiveValidation(emailCodeForm, EMAIL_CODE_SCHEMA);
  initPasswordToggles(emailForm);

  document.getElementById("email-edit").addEventListener("click", () => {
    if (!emailCodeForm.hidden) return; // Änderung läuft schon, erst Code eingeben oder abbrechen
    toggleForm(emailForm, emailForm.hidden);
  });
  emailForm.querySelector("[data-cancel]").addEventListener("click", () => toggleForm(emailForm, false));

  emailForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    showAlert(emailForm, null);
    const { valid, values } = validateForm(emailForm, EMAIL_SCHEMA);
    if (!valid) return;

    setBusy(emailForm, true);
    try {
      const result = await requestEmailChange({ newEmail: values.newEmail, password: values.password });
      toggleForm(emailForm, false);
      showEmailCodeStep(result.pending_email);
      emailCodeForm.querySelector("input").focus();
    } catch (error) {
      showServerErrors(emailForm, error);
    } finally {
      setBusy(emailForm, false);
    }
  });

  emailCodeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    showAlert(emailCodeForm, null);
    const { valid, values } = validateForm(emailCodeForm, EMAIL_CODE_SCHEMA);
    if (!valid) return;

    setBusy(emailCodeForm, true);
    try {
      account = await confirmEmailChange(values.code);
      closeEmailForms();
      render();
      showPageAlert(`Deine E-Mail-Adresse ist jetzt ${account.email}.`);
    } catch (error) {
      if (CODE_ERROR_STATUS.includes(error.status)) {
        setFieldError(emailCodeForm, "code", error.message);
        focusFirstError(emailCodeForm);
      } else {
        showAlert(emailCodeForm, error.message, "error");
      }
    } finally {
      setBusy(emailCodeForm, false);
    }
  });

  document.getElementById("email-resend").addEventListener("click", async () => {
    try {
      await resendEmailChangeCode();
      setFieldError(emailCodeForm, "code", null);
      emailCodeForm.elements.namedItem("code").value = "";
      showAlert(emailCodeForm, "Wir haben dir einen neuen Code geschickt. Der alte Code gilt nicht mehr.", "info");
    } catch (error) {
      showAlert(emailCodeForm, error.message, "error");
    }
  });

  emailCodeForm.querySelector("[data-cancel]").addEventListener("click", async () => {
    try {
      await cancelEmailChange();
    } catch {
      // Abbrechen klappt auch ohne Antwort; beim nächsten Laden zeigt die Seite den echten Stand.
    }
    account.pending_email = null;
    closeEmailForms();
  });
}

// ---------- Passwort ändern ----------

function connectPassword() {
  enableLiveValidation(passwordForm, PASSWORD_SCHEMA);
  initPasswordToggles(passwordForm);

  document.getElementById("password-edit").addEventListener("click", () =>
    toggleForm(passwordForm, passwordForm.hidden, passwordView),
  );
  passwordForm.querySelector("[data-cancel]").addEventListener("click", () =>
    toggleForm(passwordForm, false, passwordView),
  );

  passwordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    showAlert(passwordForm, null);
    const { valid, values } = validateForm(passwordForm, PASSWORD_SCHEMA);
    if (!valid) return;

    setBusy(passwordForm, true);
    try {
      await changePassword({ currentPassword: values.currentPassword, newPassword: values.newPassword });
      toggleForm(passwordForm, false, passwordView);
      showPageAlert("Dein Passwort wurde geändert. Auf anderen Geräten musst du dich neu anmelden.");
    } catch (error) {
      showServerErrors(passwordForm, error);
    } finally {
      setBusy(passwordForm, false);
    }
  });
}

// ---------- Konto löschen ----------

function connectDelete() {
  enableLiveValidation(deleteForm, DELETE_SCHEMA);
  initPasswordToggles(deleteForm);

  // Bestätigungsfenster öffnen. showModal() sperrt die Seite dahinter, Escape schließt es.
  deleteStartButton.addEventListener("click", () => {
    deleteDialog.showModal();
    deleteForm.elements.namedItem("password").focus();
  });
  deleteForm.querySelector("[data-cancel]").addEventListener("click", () => deleteDialog.close());
  // Beim Schließen (Abbrechen, Escape) Eingaben und Fehler zurücksetzen
  deleteDialog.addEventListener("close", () => resetForm(deleteForm));

  deleteForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    showAlert(deleteForm, null);
    const { valid, values } = validateForm(deleteForm, DELETE_SCHEMA);
    if (!valid) return;

    setBusy(deleteForm, true);
    try {
      await deleteAccount(values.password);
      deleteDialog.close();
      showDeleted();
    } catch (error) {
      showServerErrors(deleteForm, error);
      setBusy(deleteForm, false);
    }
  });
}

/** Alles ausblenden, Hinweis zeigen und nach kurzer Zeit zur Startseite. */
function showDeleted() {
  document.querySelector(".konto-head").hidden = true;
  document.querySelector(".konto-grid").hidden = true;
  showPageAlert(null);
  window.dispatchEvent(new CustomEvent("laserflow:avatar-changed", { detail: { avatarUrl: null } }));
  const panel = document.getElementById("konto-deleted");
  panel.hidden = false;
  panel.focus();
  window.setTimeout(() => window.location.assign("index.html"), REDIRECT_DELAY_MS);
}
