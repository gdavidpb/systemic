from dataclasses import dataclass

@dataclass
class Loyalty:
    points: int

def earn(account: Loyalty, points: int):
    if points <= 0:
        raise ValueError("positive points required")
    account.points += points

def redeem(account: Loyalty, points: int):
    if points <= 0:
        raise ValueError("positive points required")
    account.points -= points
