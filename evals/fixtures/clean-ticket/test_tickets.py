"""Tests for the ticket lifecycle.

The transition table is the specification, so the tests walk it exhaustively:
every (state, action) pair is either a declared transition or a refusal that
changes nothing.
"""

import itertools
import unittest

from .models import STATUS, TRANSITIONS, Ticket, allowed_actions
from .operations import assign, close, reopen, resolve, unassign

ACTIONS = {
    "assign": lambda t: assign(t, "agent-1"),
    "unassign": unassign,
    "resolve": resolve,
    "reopen": reopen,
    "close": close,
}

PATHS = {
    "open": [],
    "assigned": ["assign"],
    "resolved": ["assign", "resolve"],
    "closed": ["assign", "resolve", "close"],
}


def ticket_in(status):
    ticket = Ticket("t-1", "printer on fire")
    for action in PATHS[status]:
        ACTIONS[action](ticket)
    return ticket


class TransitionTableTest(unittest.TestCase):
    def test_every_state_and_action_is_a_transition_or_a_refusal(self):
        for status, action in itertools.product(sorted(STATUS), sorted(ACTIONS)):
            with self.subTest(status=status, action=action):
                ticket = ticket_in(status)
                before = vars(ticket).copy()
                applied = ACTIONS[action](ticket)
                expected = TRANSITIONS.get((status, action))
                if expected is None:
                    self.assertFalse(applied)
                    self.assertEqual(vars(ticket), before)
                else:
                    self.assertTrue(applied)
                    self.assertEqual(ticket.status, expected)
                self.assertIn(ticket.status, STATUS)

    def test_allowed_actions_match_the_table(self):
        for status in STATUS:
            expected = {a for (s, a) in TRANSITIONS if s == status}
            self.assertEqual(allowed_actions(ticket_in(status)), expected)


class LifecycleTest(unittest.TestCase):
    def test_every_action_sequence_keeps_the_field_rules(self):
        for length in range(1, 6):
            for sequence in itertools.product(sorted(ACTIONS), repeat=length):
                with self.subTest(sequence=sequence):
                    ticket = Ticket("t-1", "printer on fire")
                    for action in sequence:
                        ACTIONS[action](ticket)
                        if ticket.status == "open":
                            self.assertIsNone(ticket.assignee)
                        else:
                            self.assertIsNotNone(ticket.assignee)
                        if ticket.status in {"resolved", "closed"}:
                            self.assertIsNotNone(ticket.resolved_at)

    def test_closed_is_absorbing(self):
        ticket = ticket_in("closed")
        for action in ACTIONS.values():
            self.assertFalse(action(ticket))
        self.assertEqual(ticket.status, "closed")

    def test_applying_an_operation_twice_is_safe(self):
        for status in STATUS:
            for name, action in ACTIONS.items():
                with self.subTest(status=status, action=name):
                    ticket = ticket_in(status)
                    action(ticket)
                    after_first = vars(ticket).copy()
                    self.assertFalse(action(ticket))
                    self.assertEqual(vars(ticket), after_first)

    def test_reopen_undoes_resolve(self):
        ticket = ticket_in("assigned")
        before = vars(ticket).copy()
        resolve(ticket)
        reopen(ticket)
        self.assertEqual(vars(ticket), before)
