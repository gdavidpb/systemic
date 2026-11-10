"""Send templated emails."""

from shared.text import render


def send(mailer, to, template, **values):
    mailer.deliver(to, render(template, **values))
