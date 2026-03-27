"""
audit/auditor.py
Orchestrates the full invoice auditing pipeline:
Preprocess → OCR → Parse → Validate → Report
"""
from app.ocr.preprocess import preprocess_image
from app.ocr.extractor import extract_text
from app.parser.invoice_parser import parse_invoice
from app.validation import tax_rules, vendor_rules, duplicate, anomaly

def run_audit(image_path: str) -> dict:
    """Run the complete invoice audit pipeline on a single image.

    Args:
        image_path: Path to the raw invoice image (JPG or PNG).
    Returns:
        Dict with keys: invoice_data, flags, status (APPROVED or REVIEW).
    """
    processed = preprocess_image(image_path)
    text = extract_text(processed)
    data = parse_invoice(text)

    flags: list[str] = []
    flags += tax_rules.check(data)
    flags += vendor_rules.check(data)
    flags += duplicate.check(data)
    flags += anomaly.check(data)

    return {
        "invoice_data": data,
        "flags": flags,
        "status": "REVIEW" if flags else "APPROVED",
    }