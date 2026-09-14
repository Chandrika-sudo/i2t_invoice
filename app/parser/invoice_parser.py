from __future__ import annotations

import re
from typing import Optional


_GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b")
_TRN_RE = re.compile(r"\b1\d{14}\b")

_INV_NO_RE = re.compile(
    r"(?:INVOICE|BILL|INV)[^\w]{0,5}(?:NO|NUM|NUMBER|#)[^\w]{0,5}([\w\-/]+)",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"\b(?:\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/.\s]\d{2}[-/.\s]\d{4})\b"
)

# "PAY TO" usually identifies a payment/bank recipient, not the invoice vendor.
_VENDOR_LABEL_RE = re.compile(
    r"\b(FROM|VENDOR|SUPPLIER|SELLER|SOLD BY|ISSUED BY|REMIT TO)\b\s*:?[ \t]*",
    re.IGNORECASE,
)
_PAYMENT_LABEL_RE = re.compile(r"\bPAY TO\b\s*:?[ \t]*", re.IGNORECASE)
_CUSTOMER_LABEL_RE = re.compile(
    r"\b(ISSUED TO|BILL TO|BILLED TO|CUSTOMER)\b\s*:?[ \t]*",
    re.IGNORECASE,
)

_HEADER_NOISE_RE = re.compile(r"\b(INVOICE NO|BILL NO|DATE|DUE DATE)\b", re.IGNORECASE)

# Currency is optional. The negative lookahead prevents a percentage such as
# "10%" from being interpreted as a monetary amount.
_AMOUNT = r"(?:[$₹€£]\s*)?[\d,]+(?:\.\d{1,2})?(?![\d,.%])"

_TOTAL_LABELS = ("GRAND TOTAL", "TOTAL AMOUNT", "AMOUNT DUE", "NET PAYABLE", "TOTAL")
_TAX_LABELS = ("TOTAL TAX", "TAX AMOUNT", "VAT AMOUNT", "IGST", "CGST", "SGST", "VAT", "GST", "TAX")
_SUBTOTAL_LABELS = ("SUBTOTAL", "SUB-TOTAL", "SUB TOTAL", "TAXABLE VALUE", "TAXABLE AMOUNT", "NET AMOUNT")


def _to_float(raw: str) -> Optional[float]:
    raw = re.sub(r"[^\d.]", "", raw)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _label_amount(text: str, labels: tuple[str, ...]) -> Optional[float]:
    """Find a monetary amount after one of the supplied labels on the same line."""
    label_group = "|".join(re.escape(x).replace(r"\ ", r"\s+") for x in labels)
    pattern = re.compile(
        rf"(?im)^\s*(?:{label_group})(?:\s*\([^\n]*?\))?\s*[:=\-]?\s*({_AMOUNT})"
    )
    match = pattern.search(text)
    return _to_float(match.group(1)) if match else None


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[^\S\n]+", " ", text)


def _detect_region(text: str) -> str:
    upper = text.upper()
    if _GSTIN_RE.search(upper) or "GSTIN" in upper:
        return "IN"
    if _TRN_RE.search(upper) or "TRN" in upper or ("VAT" in upper and "GST" not in upper):
        return "AE"
    return "UNKNOWN"


def _extract_vendor(lines: list[str]) -> Optional[str]:
    """Extract only an explicitly vendor-like party; never treat PAY TO as vendor."""
    for i, line in enumerate(lines):
        if _VENDOR_LABEL_RE.search(line):
            after = _VENDOR_LABEL_RE.sub("", line).strip(" :")
            if after:
                return after
            if i + 1 < len(lines):
                candidate = lines[i + 1].strip()
                if candidate and not _CUSTOMER_LABEL_RE.search(candidate):
                    return candidate

    # If there is no explicit customer block, the first meaningful line is a
    # reasonable fallback for simple invoices whose vendor name is at the top.
    # When an ISSUED TO/BILL TO block exists, do not guess that party as vendor.
    if not any(_CUSTOMER_LABEL_RE.search(line) for line in lines):
        skip = {"invoice", "tax invoice", "bill", "receipt", "credit note", "debit note"}
        for line in lines[:5]:
            if line.lower() in skip or len(line) <= 2:
                continue
            if _HEADER_NOISE_RE.search(line):
                continue
            return line

    return None


def _extract_payment_recipient(lines: list[str]) -> Optional[str]:
    for i, line in enumerate(lines):
        if _PAYMENT_LABEL_RE.search(line):
            after = _PAYMENT_LABEL_RE.sub("", line).strip(" :")
            if after:
                return after
            if i + 1 < len(lines):
                return lines[i + 1].strip()
    return None


def _tax_percentage(text: str) -> Optional[float]:
    pattern = re.compile(
        r"(?im)^\s*(?:GST|IGST|CGST|SGST|VAT|TAX)\b[^\n]*?(\d{1,2}(?:\.\d+)?)\s*%"
    )
    match = pattern.search(text)
    return float(match.group(1)) if match else None


def parse_invoice(text: str) -> dict:
    text = _clean(text)
    upper = text.upper()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    data = {
        "doc_type": "INVOICE",
        "region": _detect_region(text),
        "invoice_no": None,
        "vendor": _extract_vendor(lines),
        "payment_recipient": _extract_payment_recipient(lines),
        "tax_id": None,
        "date": None,
        "subtotal": None,
        "tax_rate": None,
        "tax": None,
        "total": None,
    }

    if re.search(r"\bCASH\s+RECEIPT\b|\bRECEIPT\b", upper):
        data["doc_type"] = "RECEIPT"
    elif re.search(r"\bCREDIT\s+NOTE\b", upper):
        data["doc_type"] = "CREDIT_NOTE"
    elif re.search(r"\bDEBIT\s+NOTE\b", upper):
        data["doc_type"] = "DEBIT_NOTE"

    match = _INV_NO_RE.search(text)
    if match:
        data["invoice_no"] = match.group(1).upper()

    gst = _GSTIN_RE.search(upper)
    if gst:
        data["tax_id"] = gst.group(0)
    else:
        trn = _TRN_RE.search(upper)
        if trn:
            data["tax_id"] = trn.group(0)

    date_match = _DATE_RE.search(text)
    if date_match:
        data["date"] = date_match.group(0).strip()

    data["total"] = _label_amount(text, _TOTAL_LABELS)
    data["tax"] = _label_amount(text, _TAX_LABELS)
    data["subtotal"] = _label_amount(text, _SUBTOTAL_LABELS)
    data["tax_rate"] = _tax_percentage(text)

    # A tax percentage is a rate, not a monetary tax amount. If subtotal and
    # rate are known, calculate the monetary tax. Otherwise wait for arithmetic
    # derivation from subtotal + total below.
    if data["tax"] is None and data["tax_rate"] is not None and data["subtotal"] is not None:
        data["tax"] = round(data["subtotal"] * data["tax_rate"] / 100, 2)

    # Derive exactly one missing arithmetic field when the other two are known.
    if data["subtotal"] is None and data["total"] is not None and data["tax"] is not None:
        data["subtotal"] = round(data["total"] - data["tax"], 2)
    elif data["total"] is None and data["subtotal"] is not None and data["tax"] is not None:
        data["total"] = round(data["subtotal"] + data["tax"], 2)
    elif data["tax"] is None and data["subtotal"] is not None and data["total"] is not None:
        data["tax"] = round(data["total"] - data["subtotal"], 2)

    return data
