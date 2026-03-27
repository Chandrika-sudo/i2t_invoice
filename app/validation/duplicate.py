"""
validation/duplicate.py
Detects duplicate invoices via MD5 hash of (invoice_no, vendor, total).
Persists seen hashes to a CSV store.
"""
import csv, hashlib, os
from app.config.settings import INVOICE_HASH_FILE

def _build_hash(data: dict) -> str:
    """Hash on (gstin, invoice_no, vendor, total) for global uniqueness."""
    identity = (
        f"{data.get('gstin', '')}|"
        f"{data.get('invoice_no', '')}|"
        f"{data.get('vendor', '')}|"
        f"{data.get('total', '')}"
    )
    return hashlib.md5(identity.encode()).hexdigest()

def check(data: dict) -> list[str]:
    os.makedirs(os.path.dirname(INVOICE_HASH_FILE), exist_ok=True)
    h = _build_hash(data)
    if not os.path.exists(INVOICE_HASH_FILE):
        with open(INVOICE_HASH_FILE, "w", newline="") as f:
            csv.writer(f).writerow(["hash"])
    with open(INVOICE_HASH_FILE, newline="") as f:
        seen_hashes = {row[0] for row in csv.reader(f)}
    if h in seen_hashes:
        return ["Duplicate invoice detected"]
    with open(INVOICE_HASH_FILE, "a", newline="") as f:
        csv.writer(f).writerow([h])
    return []