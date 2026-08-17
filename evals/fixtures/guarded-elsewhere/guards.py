"""Status guards: mutating operators declare the statuses they accept."""

import functools


class InvalidStatus(Exception):
    pass


def requires_status(*allowed: str):
    """Reject the call before the body runs if the invoice is not in an
    allowed status. The decorated operators in operations.py form the
    transition table; this decorator is its single enforcement point."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(invoice, *args, **kwargs):
            if invoice.status not in allowed:
                raise InvalidStatus(
                    f"{fn.__name__}: not allowed from {invoice.status!r}"
                )
            return fn(invoice, *args, **kwargs)

        return wrapper

    return decorator
