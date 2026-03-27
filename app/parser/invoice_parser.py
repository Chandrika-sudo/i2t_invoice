"""
parser/invoice_parser.py
Handles Indian GST invoices and UAE VAT invoices.
Robust to Tesseract OCR noise (column collapse, symbol misreads).
"""

import re
from typing import Optional

InvoiceData = dict[str, Optional[str | float]]


def _clean_amount(raw: str) -> float:
    """Convert a string like '20,000.00' or 'AED 20,000.00' to float."""
    # Remove commas and spaces, then extract the first number (including decimals)
    raw = raw.replace(",", "").replace(" ", "")
    match = re.search(r"(\d+(?:\.\d{2})?)", raw)
    return float(match.group(1)) if match else 0.0


def _find_amounts(line: str) -> list[float]:
    """Return all amounts found in a line, left to right."""
    results = []
    # Match patterns like 123.45, 1,234.56
    for m in re.findall(r"[\d,]+\.\d{2}", line):
        try:
            val = _clean_amount(m)
            if val > 0:
                results.append(val)
        except ValueError:
            pass
    return results


def parse_invoice(text: str) -> InvoiceData:
    data: InvoiceData = {
        "doc_type": "INVOICE",
        "invoice_no": None,
        "vendor": None,
        "tax_id": None,
        "date": None,
        "subtotal": None,
        "tax": None,
        "total": None,
    }

    lines = [l.strip() for l in text.splitlines()]
    nonempty = [l for l in lines if l]
    full_upper = text.upper()

    # Document type
    if re.search(r"\bRECEIPT\b", full_upper):
        data["doc_type"] = "RECEIPT"

    # Vendor (first non‑header line)
    skip = re.compile(r"^(tax\s+invoice|invoice|receipt|bill)$", re.IGNORECASE)
    inv_label_noise = re.compile(
        r"\s+inv[a-z]*[\s.]*(?:no|num|number)[.,:\s].*$", re.IGNORECASE
    )
    for line in nonempty:
        if skip.match(line) or len(line) <= 4:
            continue
        clean = inv_label_noise.sub("", line).strip()
        if clean and len(clean) > 4:
            data["vendor"] = clean
            break

    # Invoice number
    upper_nonempty = [l.upper() for l in nonempty]
    for i, ul in enumerate(upper_nonempty):
        if re.search(r"INV[A-Z]*[\s.]*(?:NO|NUM|NUMBER)[.,:\s]", ul):
            after = re.sub(
                r".*INV[A-Z]*[\s.]*(?:NO|NUM|NUMBER)[.,:\s]*", "", ul
            ).strip()
            num_here = re.match(r"^(\d+)\b", after)
            if num_here:
                data["invoice_no"] = num_here.group(1)
                break
            for j in range(i + 1, min(i + 3, len(nonempty))):
                num_next = re.search(r"\b(\d{1,6})\b", nonempty[j])
                if num_next:
                    data["invoice_no"] = num_next.group(1)
                    break
            break

    # Tax ID (GSTIN or TRN)
    for line in nonempty:
        # Look for GSTIN label
        if re.search(r"GSTIN", line, re.IGNORECASE):
            after = re.sub(
                r".*GSTIN[A-Z/:\s\-]*", "", line, flags=re.IGNORECASE
            ).strip()
            compact = re.sub(r"\s+", "", after)[:15]
            if re.match(
                r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$",
                compact, re.IGNORECASE
            ):
                data["tax_id"] = compact.upper()
                break

        # Or find any token that looks like a GSTIN (Indian)
        for token_group in re.findall(
            r"[A-Z0-9]{5,}(?:\s[A-Z0-9]+)*", line, re.IGNORECASE
        ):
            compact = re.sub(r"\s+", "", token_group)
            if re.match(
                r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$",
                compact, re.IGNORECASE
            ):
                if not data["tax_id"]:
                    data["tax_id"] = compact.upper()

    # If not found, try TRN (UAE)
    if not data["tax_id"]:
        for line in nonempty:
            if re.search(r"\bTRN\b", line, re.IGNORECASE):
                trn = re.search(r"\b(\d{10,15})\b", line)
                if trn:
                    data["tax_id"] = trn.group(1)
                    break

    # Date
    date_m = (
        re.search(r"\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})\b", text)
        or re.search(
            r"\b(\d{1,2}[\s\-—./]+"
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"[\s\-—./]+\d{2,4})\b",
            text, re.IGNORECASE
        )
    )
    if date_m:
        data["date"] = date_m.group(1).strip()

    # Total (handle lines with currency symbols)
    CURRENCY_PREFIX = re.compile(
        r"\b(?:AED|USD|EUR|GBP|INR|SAR|QAR|OMR|BHD|KWD)\b",
        re.IGNORECASE
    )

    # First pass: look for a "total" line that contains an amount
    for line in nonempty:
        if re.match(r"total\b", line, re.IGNORECASE):
            cleaned_line = CURRENCY_PREFIX.sub("", line)
            amounts = _find_amounts(cleaned_line)
            if amounts:
                # Prefer the last amount (rightmost) as the grand total
                data["total"] = amounts[-1]
                break

    # If still missing, try "Amount Chargeable" section
    if not data["total"]:
        for line in nonempty:
            if re.search(r"amount chargeable", line, re.IGNORECASE):
                # Look for pattern like (AED 20,000.00) or just 20,000.00
                match = re.search(r"\(?AED\s*([\d,]+\.\d{2})\)?", line, re.IGNORECASE)
                if match:
                    data["total"] = _clean_amount(match.group(1))
                else:
                    amounts = _find_amounts(line)
                    if amounts:
                        data["total"] = amounts[-1]
                if data["total"]:
                    break

    # Tax (skip header lines that have no amounts)
    for line in nonempty:
        if re.search(
            r"\bIG[ST]?[ST]?\b|\bCG[ST]+\b|\bSG[ST]+\b|\bVAT\b|\bTAX\b",
            line, re.IGNORECASE
        ):
            amounts = _find_amounts(line)
            if amounts:
                # Take the last amount (likely the tax value)
                data["tax"] = amounts[-1]
                break
            # If no amounts, keep scanning (don't break)

    # Subtotal
    for line in nonempty:
        if re.search(
            r"taxable\s*(?:value|amt|amount)|sub\s*total|subtotal|exempt",
            line, re.IGNORECASE
        ):
            amounts = _find_amounts(line)
            if amounts:
                data["subtotal"] = amounts[-1]
                break

    # Derive missing fields using total and tax
    t, x, s = data["total"], data["tax"], data["subtotal"]
    if s is None and t is not None and x is not None:
        data["subtotal"] = round(t - x, 2)
    elif x is None and t is not None and s is not None:
        data["tax"] = round(t - s, 2)

    # If subtotal is still missing and tax is zero, assume subtotal = total
    if s is None and t is not None and x == 0.0:
        data["subtotal"] = t

    return data