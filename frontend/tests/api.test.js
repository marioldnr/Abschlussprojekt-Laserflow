/**
 * Tests für js/modules/api-client.js und js/modules/auth-api.js.
 * fetch wird durch eine Attrappe ersetzt, es wird kein Server gebraucht.
 */
import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import { requestJson, extractErrorMessage, ApiError, UNREACHABLE_MESSAGE } from "../js/modules/api-client.js";
import { login, register } from "../js/modules/auth-api.js";

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
    street: "Musterstraße 1", postalCode: "12345", city: "Musterstadt",
  };
  const calls = mockFetch(201, { id: 7 });
  await register(data);
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    email: "a@b.de", password: "geheim123", first_name: "Anna", last_name: "Muster",
    street: "Musterstraße 1", postal_code: "12345", city: "Musterstadt",
  });

  mockFetch(409, { detail: "exists" });
  await assert.rejects(register(data), (error) => error.status === 409 && /bereits registriert/.test(error.message));
});
