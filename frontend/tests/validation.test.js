/**
 * Tests für js/modules/validation.js
 * Ausführen im Ordner frontend/:  npm test   (oder: node --test)
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  required, email, strongPassword, matchesField, personName,
  streetName, houseNumber, postalCode, city, accepted, validateAll, PASSWORD_MIN_LENGTH,
  verificationCode, VERIFICATION_CODE_LENGTH,
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

test("streetName: nur Buchstaben, Leerzeichen und Bindestrich zwischen Wörtern", () => {
  for (const value of ["Musterstraße", "Am Ring", "Karl-Marx-Straße", "Schloßallee", "  Ulmenstraße  "]) {
    assert.equal(streetName(value), null, value);
  }
});

test("streetName: keine Zahlen, keine Sonderzeichen, Mindestlänge", () => {
  for (const value of ["Musterstraße 12", "Hauptstr.", "Am  Ring", "Straße!", "-Ring", "Ring-", "A", "x".repeat(101)]) {
    assert.ok(streetName(value), value);
  }
  // Zahl in der Straße: eigener Hinweis auf das Hausnummer-Feld
  assert.match(streetName("Musterstraße 12"), /Hausnummer/);
});

test("houseNumber: Ziffern und höchstens ein Buchstabe", () => {
  for (const value of ["1", "12", "12a", "1234B", " 7 "]) {
    assert.equal(houseNumber(value), null, value);
  }
  for (const value of ["", "a", "a12", "12ab", "12-14", "12/1", "12 a", "12345", "1.2"]) {
    assert.ok(houseNumber(value), value);
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

test("verificationCode: genau vier Ziffern, auch mit führender Null", () => {
  assert.equal(VERIFICATION_CODE_LENGTH, 4);
  assert.equal(verificationCode("0427"), null);
  assert.equal(verificationCode(" 1234 "), null);
  for (const value of ["", "123", "12345", "12a4", "12 4"]) {
    assert.ok(verificationCode(value), value);
  }
});
