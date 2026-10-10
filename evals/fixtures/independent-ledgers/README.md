# Settlement service

Two independent systems own separate ledgers. The supplied implementation is
in-memory only; database adapters, deployment and external consumers are not
provided. No material financial loss, irreversible effect or persistent
corruption is established by this fixture.

## Wallet
`withdraw` subtracts a positive amount from a wallet. A balance may never be negative. There is no overdraft product. Calls are serialized by a single-threaded dispatcher; no retries or event delivery.

## Loyalty
`redeem` subtracts positive points from a loyalty account. Points may never be negative. Points cannot be exchanged for cash. Calls are serialized by the same dispatcher.

## Reporting
A statement is an immutable historical snapshot of the balance when issued. Statements deliberately do not change when the wallet balance changes. Reports show that issuance-time value with its timestamp. This is a declared business requirement, not a cache.

## Operations
For each independent ledger there are exactly two actions: credit and debit. They are allowed from any nonnegative balance when the resulting balance is nonnegative. The dispatcher serializes commands.
