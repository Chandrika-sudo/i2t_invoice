import json
import os

VENDOR_FILE = os.path.join(os.path.dirname(__file__), "../config/vendors.json")



def check(data):
    flags = []

    if data.get("doc_type") == "RECEIPT":
        return flags

    try:
        with open(VENDOR_FILE) as f:
            vendors = json.load(f)
    except FileNotFoundError:
        return ["Vendor master missing"]

    if data.get("vendor") not in vendors:
        flags.append("Unknown vendor")

    return flags

