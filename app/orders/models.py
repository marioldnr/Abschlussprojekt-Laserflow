"""Datenbank-Tabellen des Moduls orders.

Tabellen:
    cart_items   Positionen im Warenkorb eines Kunden
    orders       abgeschlossene Bestellungen
    order_items  Positionen einer Bestellung
"""

from datetime import date, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CartItem(Base):
    """Eine Position im Warenkorb.

    Bewusste Entscheidung: Es gibt keine eigene Tabelle "Warenkorb". Der Warenkorb
    eines Kunden sind einfach alle cart_items mit seiner ``user_id``.
    """

    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    customer_image_id: Mapped[int | None] = mapped_column(ForeignKey("customer_images.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class Order(Base):
    """Eine abgeschlossene Bestellung.

    Bewusste Entscheidungen:
        - Liefer- und Rechnungsadresse werden beim Bestellen hineinkopiert
          (``ship_*``, ``bill_*``). So bleibt die Bestellung unverändert, auch wenn der
          Kunde später seine Adresse ändert oder sein Konto anonymisiert wird (US10).
        - Die Tabelle heißt ``orders``, weil ``order`` in SQL ein reserviertes Wort ist.
        - Bezahlung wird nur simuliert.

    Erlaubte Werte (als Text gespeichert, Prüfung im Service):
        status:         "ordered", "paid", "in_production", "shipped", "cancelled"
        payment_method: noch offen
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="ordered")
    ordered_at: Mapped[datetime] = mapped_column(default=datetime.now)
    expected_delivery: Mapped[date | None]
    payment_method: Mapped[str | None] = mapped_column(String(30))
    total_cent: Mapped[int]

    ship_salutation: Mapped[str | None] = mapped_column(String(20))
    ship_first_name: Mapped[str] = mapped_column(String(100))
    ship_last_name: Mapped[str] = mapped_column(String(100))
    ship_street: Mapped[str] = mapped_column(String(200))
    ship_postal_code: Mapped[str] = mapped_column(String(5))
    ship_city: Mapped[str] = mapped_column(String(100))

    bill_salutation: Mapped[str | None] = mapped_column(String(20))
    bill_first_name: Mapped[str] = mapped_column(String(100))
    bill_last_name: Mapped[str] = mapped_column(String(100))
    bill_street: Mapped[str] = mapped_column(String(200))
    bill_postal_code: Mapped[str] = mapped_column(String(5))
    bill_city: Mapped[str] = mapped_column(String(100))

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")


class OrderItem(Base):
    """Eine Position einer Bestellung.

    Bewusste Entscheidung: ``unit_price_cent`` speichert den Preis zum Zeitpunkt der
    Bestellung. Ändert sich später der Produktpreis, bleibt die Bestellung korrekt.
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    customer_image_id: Mapped[int | None] = mapped_column(ForeignKey("customer_images.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price_cent: Mapped[int]

    order: Mapped["Order"] = relationship(back_populates="items")
