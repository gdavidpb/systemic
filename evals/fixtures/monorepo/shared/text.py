"""Text helpers."""


def normalize(text):
    return text.strip().lower()


def render(template, **values):
    return template.format(**values)
