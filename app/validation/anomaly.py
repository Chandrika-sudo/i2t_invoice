"""
anomaly.py
----------
Flags statistically unusual invoices.

Checks
------
1. Amount unusually high vs historical average.
2. Tax rate outside expected band for the detected region.
3. Round-number totals (possible fabrication signal).
4. Missing critical fields.
"""

from __future__ import annotations
from app.config.settings import GST_RATE, VAT_RATE, ANOMALY_MULTIPLIER


def check(data: dict, historical_avg: float = 10_000.0) -> list[str]:
    flags: list[str] = []
    total    = data.get("total")
    tax      = data.get("tax")
    subtotal = data.get("subtotal")
    region   = data.get("region", "UNKNOWN")

    # 1. Unusually high amount
    if total is not None and total > historical_avg * ANOMALY_MULTIPLIER:
        flags.append(
            f"Invoice amount ({total:,.2f}) is {total/historical_avg:.1f}× "
            f"the historical average — manual review recommended"
        )

    # 2. Tax rate check
    if subtotal and tax and subtotal > 0:
        implied_rate = round(tax / subtotal, 4)
        expected = GST_RATE if region == "IN" else VAT_RATE
        tolerance = 0.02  # ±2 percentage points
        if abs(implied_rate - expected) > tolerance:
            flags.append(
                f"Implied tax rate {implied_rate*100:.1f}% deviates from "
                f"expected {expected*100:.0f}% for region '{region}'"
            )

    # 3. Suspicious round number (total ends in many zeros)
    if total is not None and total > 0 and total == int(total) and total % 1000 == 0:
        flags.append(f"Total ({total:,.0f}) is a suspiciously round number")

    # 4. Missing critical fields
    for field in ("invoice_no", "vendor", "total", "date"):
        if not data.get(field):
            flags.append(f"Missing field: {field}")

    return flags
