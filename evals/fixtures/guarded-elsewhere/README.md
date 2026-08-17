# Invoices module — specification

Issues invoices, collects payments through an external provider, and voids
mistakes.

## Declared state machine

```
draft → issued → paid
        issued → overdue          (nightly job, past the due date)
        issued | overdue → void   (manual correction)
        paid → issued             (a provider refund reopens the invoice)
```

- **void** is terminal. **paid** is terminal except for the declared refund
  reopening.
- Line items can change only in `draft`; once issued, an invoice is immutable
  except for its status.

## Business rules

1. The invoice total is ALWAYS the sum of its line items.
2. Only `issued` or `overdue` invoices accept payment, and the amount must
   cover the total exactly — no partial payments.
3. Only `issued` or `overdue` invoices can be voided.
4. The payment provider retries webhooks until it receives a 200. Every event
   carries a unique `event_id`; the system must tolerate duplicates.
5. A refund event reopens the paid invoice to `issued` and records the refund
   in the ledger **exactly once**.
