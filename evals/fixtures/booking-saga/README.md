# Trip booking — saga specification

Books a complete trip across three external providers. Because the providers
have no shared transaction, the booking runs as a saga: each step has a
compensating action that undoes it.

## Steps

```
reserve_flight → charge_card → reserve_hotel
```

Each step has a compensation:

| Step | Compensation |
|---|---|
| `reserve_flight` | `release_flight` |
| `charge_card` | `refund_card` |
| `reserve_hotel` | `release_hotel` |

## Guarantees

The saga guarantees exactly one of two outcomes: **the customer has a
complete trip and has been charged, or nothing happened and they were not
charged.** No third outcome is acceptable.

## Business rules

1. If any step fails, every step that already succeeded is compensated, in
   reverse order.
2. A booking is never left partially reserved — a flight with no hotel is not
   a trip.
3. The customer is never charged for a trip that was not fully booked.
4. Providers are slow and occasionally flaky, so failed operations are
   retried generously before the saga gives up.
5. Every failure raises an alert to the on-call channel so someone can act on
   it.
6. A booking that exhausts its retries goes to the dead-letter queue for
   manual review, and is drained back once the underlying problem is fixed.
