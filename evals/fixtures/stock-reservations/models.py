"""Units of stock and the table that stores them."""

from dataclasses import dataclass, replace
from datetime import datetime

RESERVATION_MINUTES = 15


@dataclass
class Unit:
    sku: str
    serial: str
    reserved_by: str | None = None
    reserved_until: datetime | None = None
    sold_at: datetime | None = None


class Store:
    """In-memory stand-in for the units table.

    get() returns a copy of the row and put() overwrites the whole row, the way
    a SELECT followed by an UPDATE of every column would.
    """

    def __init__(self):
        self.rows = {}

    def get(self, serial):
        row = self.rows.get(serial)
        return None if row is None else replace(row)

    def put(self, unit):
        self.rows[unit.serial] = replace(unit)

    def delete(self, serial):
        self.rows.pop(serial, None)

    def all(self):
        return [replace(unit) for unit in self.rows.values()]
