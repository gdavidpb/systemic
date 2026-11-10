"""HTTP entry points. Every request runs on a pool thread."""

from concurrent.futures import ThreadPoolExecutor

from .operations import release, reserve, sell

POOL = ThreadPoolExecutor(max_workers=8)


def handle(request, store, payments, now):
    """Dispatch a request. Nothing serializes requests for the same unit."""
    action = request["action"]
    if action == "reserve":
        return POOL.submit(reserve, store, request["serial"], request["shopper"], now)
    if action == "release":
        return POOL.submit(release, store, request["serial"], request["shopper"])
    if action == "sell":
        return POOL.submit(sell, store, request["serial"], request["shopper"], payments, now)
    raise ValueError(f"unknown action {action}")
