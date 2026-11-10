# Interrupted run — eval setup

Copy this directory's contents into an empty working directory before the
run. `systemic-out/orders-module/` is a run of the orders module interrupted
at F5. Since it was read in F1, `orders/operations.py` changed: `cancel()`
now refuses shipped orders.
