# Stock reservations — specification

Holds a unit of stock for a shopper during checkout, then sells it or lets the
hold lapse.

## Lifecycle of a unit

A unit has no status column. Its state is read from three fields:

| State | `reserved_by` | `reserved_until` | `sold_at` |
|---|---|---|---|
| available | `None` | `None` | `None` |
| reserved | shopper | deadline | `None` |
| sold | shopper | deadline | timestamp |

- A reservation lasts 15 minutes. When it lapses the unit is available again.
- A sold unit is never released, never expires and never changes hands.

## Business rules

1. A unit is held by at most one shopper at a time.
2. The API runs on a threaded server (`server.py`): requests for the same unit
   are processed at the same time on different threads.
3. Selling and charging happen together: if the payment provider declines, the
   unit stays reserved and is not marked sold.
4. The units table is the only record of a sale. Fulfilment reads sold units
   from it, hours after the sale. Units are never deleted.
5. Products are single SKUs. Bundles (several SKUs sold as one) are already
   requested by the catalog team for next quarter.
