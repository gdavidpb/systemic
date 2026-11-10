# Orders module — specification

Manages the order lifecycle for the store.

## Declared state machine

```
draft → pending_payment → in_review → paid → shipped → delivered
```

- **canceled**: ONLY from `draft` or `pending_payment`. A shipped order can
  never be canceled — the goods already left the warehouse.
- **on_hold**: temporary pause from any active state; every paused order must
  be able to **resume** to the state it was in.
- **in_review**: anti-fraud review before payment; every payment goes through
  here.

## Business rules

1. The order total is ALWAYS the sum of its items (qty × price).
2. Payment-provider webhooks **may arrive duplicated** (the provider retries
   until it receives a 200): the system must tolerate this.
3. An order is marked paid only when the amount paid covers the total.
4. Discounts are expressed as a **percentage** (0-100).
5. Shipping reserves inventory and notifies the courier atomically: both
   things happen, or neither does.
