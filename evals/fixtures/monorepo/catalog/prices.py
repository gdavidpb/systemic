"""Price lists per currency."""

RATES = {"USD": 1.0, "EUR": 0.92}


def convert(amount, currency):
    return round(amount * RATES[currency], 2)
