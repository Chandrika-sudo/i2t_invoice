"""
validation/anomaly.py
Flags invoices exceeding historical_avg × ANOMALY_MULTIPLIER.
"""
from app.config.settings import ANOMALY_MULTIPLIER

def check(data: dict, historical_avg: float = 10_000.0) -> list[str]:
    total = data.get("total")
    if total is None:
        return []
    if total > historical_avg * ANOMALY_MULTIPLIER:
        return ["Invoice amount unusually high"]
    return []