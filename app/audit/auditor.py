"""Orchestrates OCR, rule-based validation, and optional LLM review."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from app.config.settings import get_llm_config
from app.ocr.preprocess import preprocess_image
from app.ocr.extractor import extract_text
from app.parser.invoice_parser import parse_invoice
from app.validation import tax_rules, vendor_rules, duplicate, anomaly
from app.utils.logger import get_logger

logger = get_logger("auditor")


def run_audit(
    image_path: str,
    historical_avg: float = 10_000.0,
    use_llm: bool | None = None,
) -> dict:
    """Run OCR -> parsing -> deterministic validation -> optional AI review."""
    logger.info("Starting audit for: %s", os.path.basename(image_path))

    processed = preprocess_image(image_path)
    text = extract_text(processed)
    data = parse_invoice(text)

    logger.info(
        "Parsed — vendor=%s inv=%s total=%s region=%s",
        data.get("vendor"), data.get("invoice_no"),
        data.get("total"), data.get("region"),
    )

    rule_flags: list[str] = []
    rule_flags += tax_rules.check(data)
    rule_flags += vendor_rules.check(data)
    rule_flags += duplicate.check(data)
    rule_flags += anomaly.check(data, historical_avg=historical_avg)

    llm_config = get_llm_config()
    if use_llm is None:
        use_llm = llm_config["enabled"]

    ai_review = {
        "status": "DISABLED",
        "flagged": False,
        "confidence": 0.0,
        "issues": [],
        "error": None,
    }
    ai_flags: list[str] = []

    if use_llm:
        from app.llm.reviewer import review_to_flags

        ai_flags, ai_review = review_to_flags(text, data)

        # Do not silently call an invoice "approved" when the requested AI
        # review never completed. This is a review-state warning, not an
        # allegation that the invoice itself is wrong.
        if ai_review["status"] in {"UNAVAILABLE", "ERROR"}:
            ai_flags.append(
                f"⚠️ AI review {ai_review['status'].lower()}: "
                f"{ai_review['error'] or 'unknown AI review error'}"
            )

    flags = rule_flags + ai_flags
    status = "REVIEW" if flags else "APPROVED"

    logger.info(
        "Audit complete — status=%s rule_flags=%d ai_flags=%d",
        status, len(rule_flags), len(ai_flags),
    )

    return {
        "invoice_data": data,
        "raw_text": text,
        "flags": flags,
        "rule_flags": rule_flags,
        "ai_flags": ai_flags,
        "ai_review": ai_review,
        "status": status,
        "metadata": {
            "source_file": os.path.basename(image_path),
            "audited_at": datetime.now(timezone.utc).isoformat(),
        },
    }
