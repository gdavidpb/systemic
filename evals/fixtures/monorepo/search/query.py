"""Parse a search query into terms."""

from shared.text import normalize


def parse(query):
    return [normalize(term) for term in query.split() if term]
