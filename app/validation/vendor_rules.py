"""
validation/vendor_rules.py
Validates the vendor against the approved vendor master (vendors.json).
Skipped for RECEIPT documents.
"""
import json, os

VENDOR_FILE = os.path.join(os.path.dirname(__file__), "../config/vendors.json")

def check(data: dict) -> list[str]:
    if data.get("doc_type") == "RECEIPT":
        return []
    try:
        with open(VENDOR_FILE) as f:
            vendors: dict = json.load(f)
    except FileNotFoundError:
        return ["Vendor master missing"]
    if data.get("vendor") not in vendors:
        return ["Unknown vendor"]
    return []