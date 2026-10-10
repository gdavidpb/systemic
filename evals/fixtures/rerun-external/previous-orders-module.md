# Systemic analysis — orders module

## Executive summary
Previous review of the full local orders module: one high INCONSISTENCY.

## Findings
### [high] [INCONSISTENCY] Refunds can reopen non-paid orders
- **Check**: 3
- **Evidence**: `refunds.py:12` — `order.status = "refunded"` without a status guard; README requires paid status.
- **Systemic diagnosis**: the refund operator accepts orders in states the contract forbids.
- **Recommendation**: enforce status==paid before refunding.

## Limits and not-verified
The local refund implementation was inspected in the previous run.
