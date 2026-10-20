/**
 * Tests für js/modules/api-client.js und js/modules/auth-api.js.
 * fetch wird durch eine Attrappe ersetzt, es wird kein Server gebraucht.
 */
import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import { requestJson, extractErrorMessage, ApiError, UNREACHABLE_MESSAGE } from "../js/modules/api-client.js";
import {
  login, register, verifyCode, resendCode, getCurrentUser, logout, fieldErrorsFromApi,
} from "../js/modules/auth-api.js";

const originalFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = originalFetch;
});

/** Ersetzt fetch durch eine Attrappe, die immer dieselbe Antwort liefert, und merkt sich die Anfrage. */
function mockFetch(status, body) {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return new Response(body === undefined ? "" : JSON.stringify(body), { status });
  };
  return calls;
}

test("extractErrorMessage: liest FastAPI-Fehlerformate", () => {
  assert.equal(extractErrorMessage({ detail: "Nicht gefunden" }), "Nicht gefunden");
  assert.equal(extractErrorMessage({ detail: [{ msg: "A" }, { msg: "B" }] }), "A B");
  assert.equal(extractErrorMessage(null), null);
  assert.equal(extractErrorMessage({}), null);
});

test("requestJson: Erfolg liefert die JSON-Antwort", async () => {
  const calls = mockFetch(200, { ok: true });
  const data = await requestJson("/test", { method: "POST", body: { a: 1 } });
  assert.deepEqual(data, { ok: true });
  assert.equal(calls[0].url, "/api/test");
  assert.equal(calls[0].options.body, JSON.stringify({ a: 1 }));
});

test("requestJson: Server nicht erreichbar ergibt Status 0", async () => {
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };
  await assert.rejects(requestJson("/test"), (error) => error instanceof ApiError && error.status === 0);
});

test("requestJson: Antwort ohne JSON (z. B. HTML-Fehlerseite) wird abgefangen", async () => {
  globalThis.fetch = async () => new Response("<html>Fehler</html>", { status: 500 });
  await assert.rejects(requestJson("/test"), (error) => error.status === 500 && error.message.length > 0);
});

test("requestJson: fehlende Schnittstelle (404/405/501 ohne JSON) gilt als nicht erreichbar", async () => {
  for (const status of [404, 405, 501]) {
    globalThis.fetch = async () => new Response("", { status });
    await assert.rejects(requestJson("/test"), (error) => error.status === 0 && error.message === UNREACHABLE_MESSAGE);
  }
});

test("login: schickt getrimmte E-Mail, 401 und 403 bekommen verständliche Meldungen", async () => {
  const calls = mockFetch(200, { id: 1 });
  await login({ email: "  a@b.de ", password: "geheim123" });
  assert.equal(calls[0].url, "/api/auth/login");
  assert.deepEqual(JSON.parse(calls[0].options.body), { email: "a@b.de", password: "geheim123" });

  mockFetch(401, { detail: "Invalid credentials" });
  await assert.rejects(login({ email: "a@b.de", password: "x" }), /falsch/);

  mockFetch(403, { detail: "Not confirmed" });
  await assert.rejects(login({ email: "a@b.de", password: "x" }), /nicht bestätigt/);
});

test("register: wandelt Feldnamen ins Backend-Format, 409 = E-Mail vergeben", async () => {
  const data = {
    email: "a@b.de", password: "geheim123", firstName: " Anna ", lastName: "Muster",
    street: "Musterstraße", houseNumber: "1", postalCode: "12345", city: "Musterstadt",
  };
  const calls = mockFetch(201, { id: 7 });
  await register(data);
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    email: "a@b.de", password: "geheim123", first_name: "Anna", last_name: "Muster",
    street: "Musterstraße", house_number: "1", postal_code: "12345", city: "Musterstadt",
  });

  mockFetch(409, { detail: "exists" });
  await assert.rejects(register(data), (error) => error.status === 409 && /bereits registriert/.test(error.message));
});

test("fieldErrorsFromApi: Backend-Feldnamen werden zu Formular-Feldnamen", () => {
  const error = new ApiError("x", 422, {
    detail: [
      { loc: ["body", "postal_code"], msg: "Bitte gib eine Postleitzahl mit fünf Ziffern ein." },
      { loc: ["body", "first_name"], msg: "Name falsch" },
      { loc: ["body", "password"], msg: "Passwort zu kurz" },
      { loc: ["body", "house_number"], msg: "Hausnummer falsch" },
    ],
  });
  assert.deepEqual(fieldErrorsFromApi(error), {
    postalCode: "Bitte gib eine Postleitzahl mit fünf Ziffern ein.",
    firstName: "Name falsch",
    password: "Passwort zu kurz",
    houseNumber: "Hausnummer falsch",
  });
});

test("fieldErrorsFromApi: ohne Feldliste kommt ein leeres Objekt zurück", () => {
  assert.deepEqual(fieldErrorsFromApi(new ApiError("x", 500, null)), {});
  assert.deepEqual(fieldErrorsFromApi(new ApiError("x", 400, { detail: "Text" })), {});
});

test("register: 422 behält die Feldfehler in error.details", async () => {
  mockFetch(422, { detail: [{ loc: ["body", "email"], msg: "E-Mail ungültig" }] });
  const data = {
    email: "a@b.de", password: "geheim123", firstName: "Anna", lastName: "Muster",
    street: "Musterstraße", houseNumber: "1", postalCode: "12345", city: "Musterstadt",
  };
  await assert.rejects(register(data), (error) => error.status === 422 && fieldErrorsFromApi(error).email === "E-Mail ungültig");
});

test("verifyCode: schickt E-Mail und Code, Meldung vom Backend wird durchgereicht", async () => {
  const calls = mockFetch(200, { id: 1 });
  await verifyCode({ email: " a@b.de ", code: " 0427 " });
  assert.equal(calls[0].url, "/api/auth/verify");
  assert.deepEqual(JSON.parse(calls[0].options.body), { email: "a@b.de", code: "0427" });

  mockFetch(400, { detail: "Der Code ist falsch. Du hast noch 4 Versuche." });
  await assert.rejects(verifyCode({ email: "a@b.de", code: "1111" }), (error) => error.status === 400 && /noch 4 Versuche/.test(error.message));
});

test("resendCode und logout: leere Antwort (204) ist ein Erfolg", async () => {
  // Eigene Attrappe: Eine 204-Antwort darf gar keinen Body haben (auch keinen leeren Text).
  const urls = [];
  globalThis.fetch = async (url) => {
    urls.push(url);
    return new Response(null, { status: 204 });
  };
  assert.equal(await resendCode("a@b.de"), null);
  assert.equal(await logout(), null);
  assert.deepEqual(urls, ["/api/auth/resend-code", "/api/auth/logout"]);
});

test("getCurrentUser: 401 bedeutet nicht angemeldet (null)", async () => {
  mockFetch(200, { id: 1, first_name: "Anna" });
  assert.deepEqual(await getCurrentUser(), { id: 1, first_name: "Anna" });
  mockFetch(401, { detail: "Nicht angemeldet." });
  assert.equal(await getCurrentUser(), null);
});
