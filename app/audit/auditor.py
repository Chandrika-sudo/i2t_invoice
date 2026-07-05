"""
auditor.py
----------
Orchestrates the full pipeline: preprocess → OCR → parse → validate.
"""

from __future__ import annotations
import os
import json
from datetime import datetime

from app.ocr.preprocess import preprocess_image
from app.ocr.extractor import extract_text
from app.parser.invoice_parser import parse_invoice
from app.validation import tax_rules, vendor_rules, duplicate, anomaly
from app.utils.logger import get_logger

logger = get_logger("auditor")


def run_audit(image_path: str, historical_avg: float = 10_000.0) -> dict:
    """
    Run the complete audit pipeline on an invoice image.

    Parameters
    ----------
    image_path      : path to the raw invoice image
    historical_avg  : baseline average invoice amount for anomaly detection

    Returns
    -------
    dict with keys: invoice_data, flags, status, metadata
    """
    logger.info("Starting audit for: %s", os.path.basename(image_path))

    processed = preprocess_image(image_path)
    logger.debug("Preprocessing complete")

    text = extract_text(processed)
    logger.debug("OCR complete — extracted %d chars", len(text))

    data = parse_invoice(text)
    logger.info(
        "Parsed — vendor=%s  inv=%s  total=%s  region=%s",
        data.get("vendor"), data.get("invoice_no"),
        data.get("total"), data.get("region"),
    )

    flags: list[str] = []
    flags += tax_rules.check(data)
    flags += vendor_rules.check(data)
    flags += duplicate.check(data)
    flags += anomaly.check(data, historical_avg=historical_avg)

    status = "REVIEW" if flags else "APPROVED"
    logger.info("Audit complete — status=%s  flags=%d", status, len(flags))

    return {
        "invoice_data": data,
        "raw_text":     text,
        "flags":        flags,
        "status":       status,
        "metadata": {
            "source_file":   os.path.basename(image_path),
            "audited_at":    datetime.utcnow().isoformat() + "Z",
        },
    }
