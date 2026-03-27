"""
validation/tax_rules.py
Validates tax arithmetic. Handles:
  - Indian GST invoices (subtotal + tax = total)
  - UAE zero-VAT / exempt invoices (tax = 0, subtotal = total)
  - RECEIPT documents (skipped entirely)
"""

from app.config.settings import GST_RATE  # noqa: F401


def check(data: dict) -> list[str]:
    if data.get("doc_type") == "RECEIPT":
        return []

    flags: list[str] = []
    subtotal = data.get("subtotal")
    tax      = data.get("tax")
    total    = data.get("total")

    if subtotal is None or tax is None or total is None:
        flags.append("Missing tax fields")
        return flags

    # Zero-VAT / exempt: tax is 0 and subtotal == total — valid
    if tax == 0.0 and round(subtotal, 2) == round(total, 2):
        return []

    if round(subtotal + tax, 2) != round(total, 2):
        flags.append("Total amount mismatch")

    return flags