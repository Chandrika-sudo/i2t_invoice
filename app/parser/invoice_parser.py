from __future__ import annotations
import re
from typing import Optional


_GSTIN_RE = re.compile(
    r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b"
)

_TRN_RE = re.compile(r"\b1\d{14}\b")

_INV_NO_RE = re.compile(
    r"(?:INVOICE|BILL|INV)[^\w]{0,5}(?:NO|NUM|NUMBER|#)[^\w]{0,5}([\w\-/]+)",
    re.IGNORECASE,
)

_DATE_RE = re.compile(
    r"\b(?:\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/.\s]\d{2}[-/.\s]\d{4})\b"
)

_TAX_PCT_RE = re.compile(r"\bTAX\b.{0,20}?(\d{1,2}(?:\.\d+)?)\s?%", re.IGNORECASE)

_VENDOR_LABEL_RE = re.compile(r"\b(PAY TO|FROM|VENDOR|SOLD BY|REMIT TO)\b\s*:?\s*", re.IGNORECASE)
_HEADER_NOISE_RE = re.compile(r"\b(ISSUED TO|INVOICE NO|BILL TO|DATE|DUE DATE)\b", re.IGNORECASE)


def _first_amount(pattern: re.Pattern, text: str) -> Optional[float]:
    m = pattern.search(text)
    if m:
        raw = re.sub(r"[^\d.]", "", m.group(1))
        try:
            return float(raw)
        except ValueError:
            pass
    return None


def _build_label_amount_re(labels: list[str]) -> re.Pattern:
    label_group = "|".join(re.escape(l) for l in labels)
    return re.compile(
        rf"(?<!\w)(?:{label_group})(?!\w).{{0,50}}?([\d,]+(?:\.\d{{1,2}})?)\b",
        re.IGNORECASE,
    )


_TOTAL_RE    = _build_label_amount_re(["GRAND TOTAL", "TOTAL AMOUNT", "AMOUNT DUE", "NET PAYABLE", "TOTAL"])
_TAX_RE      = _build_label_amount_re(["IGST", "CGST", "SGST", "TOTAL TAX", "TAX AMOUNT", "VAT AMOUNT", "VAT", "GST", "TAX"])
_SUBTOTAL_RE = _build_label_amount_re(["SUBTOTAL", "SUB-TOTAL", "SUB TOTAL", "TAXABLE VALUE", "TAXABLE AMOUNT", "NET AMOUNT"])


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[^\S\n]+", " ", text)
    return text


def _detect_region(text: str) -> str:
    upper = text.upper()
    if _GSTIN_RE.search(upper) or "GSTIN" in upper:
        return "IN"
    if _TRN_RE.search(upper) or "TRN" in upper or ("VAT" in upper and "GST" not in upper):
        return "AE"
    return "UNKNOWN"


def _extract_vendor(lines: list[str]) -> Optional[str]:
    for i, line in enumerate(lines):
        if _VENDOR_LABEL_RE.search(line):
            after = _VENDOR_LABEL_RE.sub("", line).strip()
            if after:
                return after
            if i + 1 < len(lines):
                return lines[i + 1].strip()

    skip_keywords = {"invoice", "tax invoice", "bill", "receipt", "credit note", "debit note"}
    for line in lines[:5]:
        if line.lower() in skip_keywords or len(line) <= 2:
            continue
        if _HEADER_NOISE_RE.search(line):
            continue
        return line
    return None


def parse_invoice(text: str) -> dict:
    text = _clean(text)
    upper = text.upper()
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    data: dict = {
        "doc_type":   "INVOICE",
        "region":     _detect_region(text),
        "invoice_no": None,
        "vendor":     None,
        "tax_id":     None,
        "date":       None,
        "subtotal":   None,
        "tax":        None,
        "total":      None,
    }

    if re.search(r"\bCASH\s+RECEIPT\b|\bRECEIPT\b", upper):
        data["doc_type"] = "RECEIPT"
    elif re.search(r"\bCREDIT\s+NOTE\b", upper):
        data["doc_type"] = "CREDIT_NOTE"
    elif re.search(r"\bDEBIT\s+NOTE\b", upper):
        data["doc_type"] = "DEBIT_NOTE"

    data["vendor"] = _extract_vendor(lines)

    m = _INV_NO_RE.search(text)
    if m:
        data["invoice_no"] = m.group(1).upper()

    gst = _GSTIN_RE.search(upper)
    if gst:
        data["tax_id"] = gst.group(0)
    else:
        trn = _TRN_RE.search(upper)
        if trn:
            data["tax_id"] = trn.group(0)

    d = _DATE_RE.search(text)
    if d:
        data["date"] = d.group(0).strip()

    data["total"]    = _first_amount(_TOTAL_RE,    text) or _first_amount(_TOTAL_RE,    upper)
    data["tax"]      = _first_amount(_TAX_RE,      text) or _first_amount(_TAX_RE,      upper)
    data["subtotal"] = _first_amount(_SUBTOTAL_RE, text) or _first_amount(_SUBTOTAL_RE, upper)

    if data["tax"] is None:
        pct = _TAX_PCT_RE.search(text)
        if pct and data["subtotal"] is not None:
            data["tax"] = round(data["subtotal"] * float(pct.group(1)) / 100, 2)

    if data["total"] is not None and data["tax"] is not None and data["subtotal"] is None:
        data["subtotal"] = round(data["total"] - data["tax"], 2)
    elif data["subtotal"] is not None and data["tax"] is not None and data["total"] is None:
        data["total"] = round(data["subtotal"] + data["tax"], 2)
    elif data["subtotal"] is not None and data["total"] is not None and data["tax"] is None:
        data["tax"] = round(data["total"] - data["subtotal"], 2)

    return data