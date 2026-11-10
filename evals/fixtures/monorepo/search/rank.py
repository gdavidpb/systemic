"""Rank products by how many query terms their name contains."""


def rank(products, terms):
    return sorted(products, key=lambda p: -sum(t in p.name.lower() for t in terms))
