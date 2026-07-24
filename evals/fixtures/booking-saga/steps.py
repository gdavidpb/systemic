"""Saga steps and their compensations."""

from dataclasses import dataclass, field


@dataclass
class Booking:
    id: str
    customer_id: str
    flight_ref: str | None = None
    hotel_ref: str | None = None
    charge_ref: str | None = None
    completed: list[str] = field(default_factory=list)


def reserve_flight(booking: Booking, providers) -> None:
    booking.flight_ref = providers.airline.reserve(booking.id)


def release_flight(booking: Booking, providers) -> None:
    providers.airline.release(booking.flight_ref)


def charge_card(booking: Booking, providers) -> None:
    booking.charge_ref = providers.payments.charge(
        booking.customer_id, booking.id
    )


def refund_card(booking: Booking, providers) -> None:
    providers.payments.refund(booking.charge_ref)


def reserve_hotel(booking: Booking, providers) -> None:
    booking.hotel_ref = providers.hotel.reserve(booking.id)


def release_hotel(booking: Booking, providers) -> None:
    providers.hotel.release(booking.hotel_ref)


STEPS = [
    ("reserve_flight", reserve_flight, release_flight),
    ("charge_card", charge_card, refund_card),
    ("reserve_hotel", reserve_hotel, release_hotel),
]
