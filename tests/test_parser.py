"""
Unit tests for invoice_parser.py
Run with: pytest tests/
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.parser.invoice_parser import parse_invoice


SAMPLE_GST = """
ACME Traders Pvt. Ltd.
TAX INVOICE
Invoice No: INV-2024-0042
Date: 15/03/2024
GSTIN: 27AAPFU0939F1ZV

Description          Amount
Widget A x10         8,474.58
GST (18%):           1,525.42
TOTAL:              10,000.00
"""

SAMPLE_UAE = """
Gulf Supplies LLC
TAX INVOICE
Invoice No: INV-AE-0099
Date: 20/03/2024
TRN: 100234567890123

Services rendered      9,523.81
VAT (5%):                476.19
TOTAL:                10,000.00
"""

SAMPLE_OCR_NOISE = """
ACME TRADERS PVT LTD
TAX|INVOICE
InvoiceNo:INV-2024-0043
Date:16/03/2024
GSTIN:27AAPFU0939F1ZV
SUBTOTAL: 8474.58
GST:1525.42
TOTAL:10000.00
"""


def test_gst_invoice_region():
    d = parse_invoice(SAMPLE_GST)
    assert d["region"] == "IN"


def test_gst_gstin_extracted():
    d = parse_invoice(SAMPLE_GST)
    assert d["tax_id"] == "27AAPFU0939F1ZV"


def test_uae_invoice_region():
    d = parse_invoice(SAMPLE_UAE)
    assert d["region"] == "AE"


def test_uae_trn_extracted():
    d = parse_invoice(SAMPLE_UAE)
    assert d["tax_id"] == "100234567890123"


def test_total_parsed():
    d = parse_invoice(SAMPLE_GST)
    assert d["total"] == 10000.00


def test_subtotal_derived():
    d = parse_invoice(SAMPLE_GST)
    assert d["subtotal"] == 8474.58


def test_invoice_number():
    d = parse_invoice(SAMPLE_GST)
    assert d["invoice_no"] == "INV-2024-0042"


def test_ocr_noise_tolerant():
    d = parse_invoice(SAMPLE_OCR_NOISE)
    assert d["total"] == 10000.00
    assert d["tax"] == 1525.42


def test_date_parsed():
    d = parse_invoice(SAMPLE_GST)
    assert "15" in d["date"] and "2024" in d["date"]


def test_vendor_first_line():
    d = parse_invoice(SAMPLE_GST)
    assert "ACME" in d["vendor"]
