import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

RAW_DIR           = os.path.join(BASE_DIR, "data", "raw_invoices")
PROCESSED_DIR     = os.path.join(BASE_DIR, "data", "processed_images")
TEXT_DIR          = os.path.join(BASE_DIR, "data", "extracted_text")
INVOICE_HASH_FILE = os.path.join(BASE_DIR, "data", "invoice_hashes.csv")

# Tax rates
GST_RATE          = 0.18   # India  — standard GST rate
VAT_RATE          = 0.05   # UAE    — standard VAT rate

# Anomaly detection
ANOMALY_MULTIPLIER = 1.5   # flag invoices > avg * this
