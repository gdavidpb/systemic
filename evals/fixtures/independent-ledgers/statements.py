from dataclasses import dataclass
from datetime import datetime, UTC
from .wallet import Wallet

@dataclass(frozen=True)
class Statement:
    balance_at_issue: int
    issued_at: datetime

def issue_statement(wallet: Wallet) -> Statement:
    return Statement(wallet.balance, datetime.now(UTC))
