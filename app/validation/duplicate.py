"""
duplicate.py
------------
Detects duplicate invoices using a persistent MD5 fingerprint store.

Fingerprint = MD5(invoice_no + vendor + total)
Stored in a CSV so it survives process restarts.
"""

from __future__ import annotations
import csv
import os

from app.config.settings import INVOICE_HASH_FILE
from app.utils.hash_utils import invoice_fingerprint


def check(data: dict) -> list[str]:
    invoice_no = data.get("invoice_no") or ""
    vendor     = data.get("vendor") or ""
    total      = data.get("total") or 0.0

    h = invoice_fingerprint(str(invoice_no), str(vendor), float(total))

    os.makedirs(os.path.dirname(INVOICE_HASH_FILE), exist_ok=True)

    # Ensure file exists with header
    if not os.path.exists(INVOICE_HASH_FILE):
        with open(INVOICE_HASH_FILE, "w", newline="") as f:
            csv.writer(f).writerow(["hash"])

    # Read existing hashes
    with open(INVOICE_HASH_FILE, newline="") as f:
        known = {row[0] for row in csv.reader(f) if row}

    if h in known:
        return [f"Duplicate invoice detected (fingerprint: {h[:8]}…)"]

    # Register new hash
    with open(INVOICE_HASH_FILE, "a", newline="") as f:
        csv.writer(f).writerow([h])

    return []
