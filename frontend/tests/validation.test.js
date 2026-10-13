/**
 * Tests für js/modules/validation.js
 * Ausführen im Ordner frontend/:  npm test   (oder: node --test)
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  required, email, strongPassword, matchesField, personName,
  street, postalCode, city, accepted, validateAll, PASSWORD_MIN_LENGTH,
} from "../js/modules/validation.js";

test("required: leere und nur aus Leerzeichen bestehende Werte sind ungültig", () => {
  assert.ok(required(""));
  assert.ok(required("   "));
  assert.ok(required(undefined));
  assert.equal(required("x"), null);
});

test("email: gültige Adressen", () => {
  for (const value of ["name@beispiel.de", "vor.nach+shop@mail.example.com", "  a@b.io  "]) {
    assert.equal(email(value), null, value);
  }
});

test("email: ungültige Adressen", () => {
  for (const value of ["", "name", "name@", "@beispiel.de", "name@beispiel", "na me@beispiel.de", "name@beispiel.d"]) {
    assert.ok(email(value), value);
  }
});

test("strongPassword: Grenzfall Mindestlänge", () => {
  const sevenChars = "abc1234";
  const eightChars = "abcd1234";
  assert.equal(sevenChars.length, PASSWORD_MIN_LENGTH - 1);
  assert.ok(strongPassword(sevenChars));
  assert.equal(strongPassword(eightChars), null);
});

test("strongPassword: braucht Buchstabe und Ziffer", () => {
  assert.ok(strongPassword("12345678"));
  assert.ok(strongPassword("abcdefgh"));
  assert.equal(strongPassword("Äpfel2026"), null); // Umlaute zählen als Buchstaben
});

test("matchesField: Passwörter müssen übereinstimmen", () => {
  const rule = matchesField("password");
  assert.equal(rule("geheim123", { password: "geheim123" }), null);
  assert.ok(rule("geheim124", { password: "geheim123" }));
});

test("personName: Buchstaben, Bindestrich, Umlaute; keine Ziffern; Längengrenzen", () => {
  assert.equal(personName("Anna-Lena"), null);
  assert.equal(personName("Müller"), null);
  assert.equal(personName("O'Brien"), null);
  assert.ok(personName("A"));
  assert.ok(personName("R2D2"));
  assert.ok(personName("x".repeat(51)));
  assert.equal(personName("x".repeat(50)), null);
});

test("street: braucht Straßenname und Hausnummer", () => {
  for (const value of ["Musterstraße 12", "Am Ring 3a", "Hauptstr. 7", "Lange Gasse 10-12"]) {
    assert.equal(street(value), null, value);
  }
  for (const value of ["Musterstraße", "12", "Musterstraße zwölf", ""]) {
    assert.ok(street(value), value);
  }
});

test("postalCode: genau fünf Ziffern", () => {
  assert.equal(postalCode("12345"), null);
  assert.equal(postalCode(" 01067 "), null);
  assert.ok(postalCode("1234"));
  assert.ok(postalCode("123456"));
  assert.ok(postalCode("12a45"));
});

test("city: Ortsnamen", () => {
  assert.equal(city("Frankfurt am Main"), null);
  assert.equal(city("Bad Homburg v. d. Höhe"), null);
  assert.ok(city("B"));
  assert.ok(city("Berlin 10"));
});

test("accepted: nur true ist gültig", () => {
  assert.equal(accepted(true), null);
  assert.ok(accepted(false));
  assert.ok(accepted("true"));
});

test("validateAll: sammelt nur die Fehler der ungültigen Felder, erste Regel gewinnt", () => {
  const schema = { email: [required, email], password: [required] };
  assert.deepEqual(validateAll({ email: "a@b.de", password: "x" }, schema), {});
  const errors = validateAll({ email: "", password: "" }, schema);
  assert.deepEqual(Object.keys(errors).sort(), ["email", "password"]);
  assert.equal(errors.email, required(""));
});
