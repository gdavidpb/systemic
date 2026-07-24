# Equipment rental — design document

Customers rent equipment (cameras, drones, tools) for a daily rate, leaving a
deposit. Lockers handle physical pickup and return; a locker webhook notifies
our system of each physical event.

## Lifecycle

States: `requested → approved → active → returned → closed`, plus `overdue`.

- **requested**: the customer picked equipment and dates; awaiting review.
- **approved**: reviewed and reserved. The invoice total is computed and
  stored at approval time (daily_rate × days + deposit).
- **active**: the customer picked the equipment up from the locker.
- **overdue**: the return date passed and the equipment was not returned.
  Overdue rentals can never be extended — the customer must return the
  equipment and open a new rental.
- **returned**: the locker registered the physical return. The deposit is
  refunded when the item is returned in good condition.
- **closed**: refund settled and rental archived.

## Operations

- `approve(rental)` — review passes; reserves the equipment for the dates.
- `pickup(rental)` — fired by the locker webhook on physical pickup.
- `extend(rental, days)` — adds days to an active rental. The price of the
  extension uses the current daily rate. Example: a customer two days late
  realizes they need the drone one more week, extends the rental and pays
  the difference.
- `return_event(rental)` — fired by the locker webhook on physical return.
  Each return event closes the rental and triggers the deposit refund. Note:
  the locker system may fire the same event multiple times when its network
  is flaky.
- `close(rental)` — settles the refund and archives the rental.

## Business rules

1. Equipment can only be reserved for one rental at a time.
2. The rental price is always daily_rate × days actually rented.
3. A rental suspended for a quality claim does not accrue daily charges.
4. Lost items are handled by the support team outside the system.
5. Deposits are refunded in full unless damage is registered.
