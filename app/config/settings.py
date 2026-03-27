"""
config/settings.py
Central configuration. Override values via .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

RAW_DIR       = os.path.join(BASE_DIR, "data/raw_invoices")
PROCESSED_DIR = os.path.join(BASE_DIR, "data/processed_images")
TEXT_DIR      = os.path.join(BASE_DIR, "data/extracted_text")

INVOICE_HASH_FILE = os.path.join(BASE_DIR, "data/invoice_hashes.csv")

GST_RATE:           float = float(os.getenv("GST_RATE", "0.18"))
ANOMALY_MULTIPLIER: float = float(os.getenv("ANOMALY_MULTIPLIER", "1.5"))