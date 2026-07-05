from app.config.settings import GST_RATE



def check(data):
    flags = []

    # Receipts often include tax in total → skip strict checks
    if data.get("doc_type") == "RECEIPT":
        return flags

    subtotal = data.get("subtotal")
    tax = data.get("tax")
    total = data.get("total")

    if subtotal is None or tax is None or total is None:
        flags.append("Missing tax fields")
        return flags

    if round(subtotal + tax, 2) != round(total, 2):
        flags.append("Total amount mismatch")

    return flags

