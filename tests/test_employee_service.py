"""Tests für app/accounts/employee_service.py (US15: Mitarbeiteraccounts verwalten).

Normalfall, ungültige Eingaben und Grenzfälle. Jeder Test bekommt über die Fixture
``db`` eine leere Datenbank im Arbeitsspeicher.
"""

import pytest

from app.accounts import employee_service
from app.accounts.employee_service import EmployeeInactiveError, EmployeeNotFoundError, LastAdminError
from app.accounts.models import User
from app.accounts.service import (
    EmailAlreadyRegisteredError,
    FieldValidationError,
    InvalidCredentialsError,
    authenticate,
    hash_password,
)
from scripts.seed_db import main, seed_first_admin


def create(db, email="max@example.de", role="employee", **changes):
    """Legt einen Mitarbeiter mit gültigen Standardwerten an."""
    data = {"password": "geheim123", "first_name": "Max", "last_name": "Muster"} | changes
    return employee_service.create_employee(db, email, data["password"], data["first_name"], data["last_name"], role)


def update(db, user, **changes):
    """Ruft update_employee mit den aktuellen Werten auf, nur ``changes`` werden geändert."""
    data = {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "is_active": user.is_active,
        "password": None,
    } | changes
    return employee_service.update_employee(db, user.id, **data)


# --------------------------------------------------------------------------- Anlegen


def test_create_employee_is_verified_and_can_log_in(db):
    user = create(db, email="  Max@Example.de ")

    assert user.id is not None
    assert user.email == "max@example.de"  # normalisiert
    assert user.role == "employee"
    assert user.is_verified is True  # kein Bestätigungscode nötig
    assert user.is_active is True
    assert authenticate(db, "max@example.de", "geheim123").id == user.id


def test_create_admin(db):
    assert create(db, role="admin").role == "admin"


def test_password_is_stored_as_hash(db):
    user = create(db)
    assert "geheim123" not in user.password_hash


def test_all_invalid_fields_are_reported_at_once(db):
    with pytest.raises(FieldValidationError) as error:
        employee_service.create_employee(db, "keine-mail", "kurz", "M", "", "customer")

    assert set(error.value.errors) == {"email", "password", "first_name", "last_name", "role"}
    assert db.query(User).count() == 0


@pytest.mark.parametrize("role", ["customer", "Admin", "", "chef"])
def test_only_employee_and_admin_roles_are_allowed(db, role):
    with pytest.raises(FieldValidationError) as error:
        create(db, role=role)
    assert "role" in error.value.errors


def test_email_taken_by_customer_is_rejected(db):
    db.add(User(email="anna@example.de", password_hash=hash_password("geheim123"), role="customer"))
    db.commit()

    with pytest.raises(EmailAlreadyRegisteredError):
        create(db, email="ANNA@example.de")


# --------------------------------------------------------------------------- Auflisten und holen


def test_list_contains_employees_and_admins_but_no_customers(db):
    db.add(User(email="kunde@example.de", password_hash="x", role="customer"))
    db.commit()
    zoe = create(db, email="zoe@example.de", last_name="Zander")
    anna = create(db, email="anna@example.de", last_name="Adler", role="admin")

    assert [user.id for user in employee_service.list_employees(db)] == [anna.id, zoe.id]


def test_list_is_empty_without_employees(db):
    assert employee_service.list_employees(db) == []


def test_get_employee_unknown_id_or_customer_is_not_found(db):
    customer = User(email="kunde@example.de", password_hash="x", role="customer")
    db.add(customer)
    db.commit()

    with pytest.raises(EmployeeNotFoundError):
        employee_service.get_employee(db, 999)
    with pytest.raises(EmployeeNotFoundError):
        employee_service.get_employee(db, customer.id)


# --------------------------------------------------------------------------- Bearbeiten


def test_update_changes_data_and_role(db):
    create(db, email="chef@example.de", role="admin")
    user = create(db)

    updated = update(db, user, first_name="Maximilian", email="neu@example.de", role="admin")

    assert updated.first_name == "Maximilian"
    assert updated.email == "neu@example.de"
    assert updated.role == "admin"


def test_update_without_password_keeps_old_password(db):
    user = create(db)
    old_hash = user.password_hash

    update(db, user, first_name="Moritz", password="")

    assert user.password_hash == old_hash
    assert authenticate(db, "max@example.de", "geheim123")


def test_update_with_new_password(db):
    user = create(db)
    update(db, user, password="neuesPasswort1")
    assert authenticate(db, "max@example.de", "neuesPasswort1")


def test_update_rejects_weak_new_password(db):
    user = create(db)
    with pytest.raises(FieldValidationError) as error:
        update(db, user, password="kurz")
    assert "password" in error.value.errors


def test_update_keeping_own_email_is_fine_but_foreign_email_is_rejected(db):
    create(db, email="anna@example.de")
    user = create(db)

    update(db, user, email="max@example.de")  # eigene E-Mail: kein Fehler
    with pytest.raises(EmailAlreadyRegisteredError):
        update(db, user, email="anna@example.de")


def test_deactivated_employee_can_no_longer_log_in(db):
    user = create(db)
    update(db, user, is_active=False)

    assert user.is_active is False
    with pytest.raises(InvalidCredentialsError):
        authenticate(db, "max@example.de", "geheim123")


def test_deactivated_employee_cannot_be_reactivated(db):
    user = create(db)
    update(db, user, is_active=False)

    with pytest.raises(EmployeeInactiveError):
        update(db, user, is_active=True)
    assert user.is_active is False


def test_deactivated_employee_cannot_be_edited(db):
    user = create(db)
    update(db, user, is_active=False)

    with pytest.raises(EmployeeInactiveError):
        update(db, user, first_name="Moritz")
    with pytest.raises(EmployeeInactiveError):
        update(db, user, password="neuesPasswort1")
    assert user.first_name == "Max"


def test_update_unknown_employee_is_not_found(db):
    with pytest.raises(EmployeeNotFoundError):
        employee_service.update_employee(db, 999, "a@example.de", "Max", "Muster", "employee", True)


def test_last_active_admin_cannot_be_demoted_or_deactivated(db):
    admin = create(db, role="admin")

    with pytest.raises(LastAdminError):
        update(db, admin, role="employee")
    with pytest.raises(LastAdminError):
        update(db, admin, is_active=False)


def test_admin_can_be_demoted_when_another_admin_exists(db):
    first = create(db, email="eins@example.de", role="admin")
    create(db, email="zwei@example.de", role="admin")

    assert update(db, first, role="employee").role == "employee"


# --------------------------------------------------------------------------- Startdaten (scripts/seed_db.py)


def test_seed_first_admin_creates_admin_once(db):
    admin = seed_first_admin(db, "admin@laserflow.local", "geheim123")

    assert admin.role == "admin"
    assert seed_first_admin(db, "admin@laserflow.local", "geheim123") is None  # zweiter Start ändert nichts
    assert db.query(User).count() == 1


def test_seed_first_admin_saves_given_name(db):
    admin = seed_first_admin(db, "admin@laserflow.local", "geheim123", first_name="Mario", last_name="Lindner")

    assert db.get(User, admin.id).first_name == "Mario"
    assert db.get(User, admin.id).last_name == "Lindner"


def test_seed_first_admin_rejects_invalid_name_and_creates_nothing(db):
    with pytest.raises(FieldValidationError) as error:
        seed_first_admin(db, "admin@laserflow.local", "geheim123", first_name="M4rio")

    assert "first_name" in error.value.errors
    assert db.query(User).count() == 0


def run_main(monkeypatch, db, answers):
    """Startet scripts.seed_db.main() mit festen Antworten auf die Eingaben.

    ``answers`` sind die Antworten auf input() in dieser Reihenfolge, das Passwort kommt
    von getpass(). Die Test-Datenbank ``db`` ersetzt die echte laserflow.db, und
    init_db() wird nicht ausgeführt (die Tabellen gibt die Fixture schon).
    """
    remaining = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(remaining))
    monkeypatch.setattr("scripts.seed_db.getpass", lambda prompt="": "geheim123")
    monkeypatch.setattr("scripts.seed_db.SessionLocal", lambda: db)
    monkeypatch.setattr("scripts.seed_db.init_db", lambda: None)
    monkeypatch.setattr(db, "close", lambda: None)  # die Fixture schließt die Session selbst
    main()


def test_main_asks_for_name_and_saves_it(db, monkeypatch, capsys):
    run_main(monkeypatch, db, ["admin@laserflow.local", "Mario", "Lindner"])

    assert "Mario Lindner" in capsys.readouterr().out
    assert db.query(User).one().first_name == "Mario"


def test_main_prints_reason_for_invalid_name(db, monkeypatch, capsys):
    run_main(monkeypatch, db, ["admin@laserflow.local", "M4rio", "Lindner"])

    assert "Nicht angelegt:" in capsys.readouterr().out
    assert db.query(User).count() == 0
