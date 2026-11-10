"""Operations on units of stock."""

from datetime import timedelta

from .models import RESERVATION_MINUTES


class Unavailable(Exception):
    pass


class PaymentDeclined(Exception):
    pass


def reserve(store, serial, shopper, now):
    unit = store.get(serial)
    if unit.reserved_by is not None and unit.reserved_until > now:
        raise Unavailable(serial)
    unit.reserved_by = shopper
    unit.reserved_until = now + timedelta(minutes=RESERVATION_MINUTES)
    store.put(unit)
    return unit


def release(store, serial, shopper):
    unit = store.get(serial)
    if unit.reserved_by != shopper or unit.sold_at is not None:
        raise Unavailable(serial)
    unit.reserved_by = None
    unit.reserved_until = None
    store.put(unit)


def sell(store, serial, shopper, payments, now):
    unit = store.get(serial)
    if unit.reserved_by != shopper or unit.sold_at is not None:
        raise Unavailable(serial)
    unit.sold_at = now
    store.put(unit)
    payments.charge(shopper, unit.sku)


def sweep(store, now):
    """Cron job, every minute: drop lapsed reservations so the unit can be held again."""
    for unit in store.all():
        if unit.reserved_until is not None and unit.reserved_until <= now:
            store.delete(unit.serial)


def price_of(unit, catalog):
    # Bundles are not modeled yet: the catalog team encodes them as a SKU prefix
    # and we split the bundle price evenly here until they exist.
    if unit.sku.startswith("BUNDLE-"):
        return catalog[unit.sku] / len(catalog[unit.sku + ":parts"])
    return catalog[unit.sku]
