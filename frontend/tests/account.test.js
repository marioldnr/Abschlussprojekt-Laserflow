/**
 * Tests für js/modules/account-api.js ("Mein Konto", US10).
 * fetch wird durch eine Attrappe ersetzt, es wird kein Server gebraucht.
 */
import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import { ApiError } from "../js/modules/api-client.js";
import { fieldErrorsFromApi } from "../js/modules/auth-api.js";
import {
  checkAvatarFile, AVATAR_MAX_BYTES, getAccount, updateProfile, changePassword, requestEmailChange,
  confirmEmailChange, uploadAvatar, removeAvatar, deleteAccount,
} from "../js/modules/account-api.js";

const originalFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = originalFetch;
});

/** Attrappe für fetch: merkt sich die Anfragen und antwortet immer gleich. */
function mockFetch(status, body) {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    if (status === 204) return new Response(null, { status });
    return new Response(JSON.stringify(body ?? {}), { status });
  };
  return calls;
}

test("checkAvatarFile: erlaubte Formate und Größe", () => {
  assert.equal(checkAvatarFile({ type: "image/jpeg", size: 1000 }), null);
  assert.equal(checkAvatarFile({ type: "image/png", size: AVATAR_MAX_BYTES }), null); // Grenzfall: genau 5 MB
  assert.equal(checkAvatarFile({ type: "image/webp", size: 1 }), null);
});

test("checkAvatarFile: falsches Format, zu groß, keine Datei", () => {
  assert.match(checkAvatarFile({ type: "image/gif", size: 10 }), /JPG, PNG oder WebP/);
  assert.match(checkAvatarFile({ type: "application/pdf", size: 10 }), /JPG, PNG oder WebP/);
  assert.match(checkAvatarFile({ type: "image/png", size: AVATAR_MAX_BYTES + 1 }), /5 MB/);
  assert.ok(checkAvatarFile(null));
});

test("getAccount: GET /api/account", async () => {
  const calls = mockFetch(200, { email: "a@b.de" });
  assert.deepEqual(await getAccount(), { email: "a@b.de" });
  assert.equal(calls[0].url, "/api/account");
  assert.equal(calls[0].options.method, "GET");
});

test("updateProfile: Formularnamen werden zu Backend-Namen, Leerzeichen entfernt", async () => {
  const calls = mockFetch(200, {});
  await updateProfile({
    firstName: " Anna ", lastName: "Muster", street: "Am Ring", houseNumber: " 3a ", postalCode: "12345", city: "Köln",
  });
  assert.equal(calls[0].url, "/api/account/profile");
  assert.equal(calls[0].options.method, "PUT");
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    first_name: "Anna", last_name: "Muster", street: "Am Ring", house_number: "3a", postal_code: "12345", city: "Köln",
  });
});

test("changePassword und requestEmailChange: richtige Felder", async () => {
  let calls = mockFetch(204);
  await changePassword({ currentPassword: "alt12345", newPassword: "neu12345" });
  assert.deepEqual(JSON.parse(calls[0].options.body), { current_password: "alt12345", new_password: "neu12345" });

  calls = mockFetch(202, { pending_email: "neu@b.de" });
  const result = await requestEmailChange({ newEmail: " neu@b.de ", password: "geheim123" });
  assert.equal(result.pending_email, "neu@b.de");
  assert.deepEqual(JSON.parse(calls[0].options.body), { new_email: "neu@b.de", password: "geheim123" });
});

test("confirmEmailChange: Code falsch → Meldung vom Backend", async () => {
  mockFetch(400, { detail: "Der Code ist falsch. Du hast noch 4 Versuche." });
  await assert.rejects(confirmEmailChange("1111"), (error) => error.status === 400 && /noch 4/.test(error.message));
});

test("uploadAvatar: schickt die Datei unverändert mit ihrem Typ", async () => {
  const calls = mockFetch(200, { avatar_url: "/api/account/avatar?v=1-abc" });
  const file = new Blob([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], { type: "image/png" });
  const result = await uploadAvatar(file);
  assert.equal(result.avatar_url, "/api/account/avatar?v=1-abc");
  assert.equal(calls[0].url, "/api/account/avatar");
  assert.equal(calls[0].options.method, "PUT");
  assert.equal(calls[0].options.headers["Content-Type"], "image/png");
  assert.equal(calls[0].options.body, file);
});

test("removeAvatar und deleteAccount", async () => {
  let calls = mockFetch(204);
  assert.equal(await removeAvatar(), null);
  assert.equal(calls[0].options.method, "DELETE");

  calls = mockFetch(204);
  await deleteAccount("geheim123");
  assert.equal(calls[0].url, "/api/account/delete");
  assert.deepEqual(JSON.parse(calls[0].options.body), { password: "geheim123" });
});

test("fieldErrorsFromApi: Feldnamen von Mein Konto", () => {
  const error = new ApiError("x", 422, {
    detail: [
      { loc: ["body", "current_password"], msg: "Das Passwort ist falsch." },
      { loc: ["body", "new_email"], msg: "Bereits registriert" },
      { loc: ["body", "avatar"], msg: "Falsches Format" },
    ],
  });
  assert.deepEqual(fieldErrorsFromApi(error), {
    currentPassword: "Das Passwort ist falsch.",
    newEmail: "Bereits registriert",
    avatar: "Falsches Format",
  });
});
