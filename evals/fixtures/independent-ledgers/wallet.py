from dataclasses import dataclass

@dataclass
class Wallet:
    balance: int

def credit(wallet: Wallet, amount: int):
    if amount <= 0:
        raise ValueError("positive amount required")
    wallet.balance += amount

def withdraw(wallet: Wallet, amount: int):
    if amount <= 0:
        raise ValueError("positive amount required")
    wallet.balance -= amount
