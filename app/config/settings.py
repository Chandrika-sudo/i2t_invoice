import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

RAW_DIR           = os.path.join(BASE_DIR, "data", "raw_invoices")
PROCESSED_DIR     = os.path.join(BASE_DIR, "data", "processed_images")
TEXT_DIR          = os.path.join(BASE_DIR, "data", "extracted_text")
INVOICE_HASH_FILE = os.path.join(BASE_DIR, "data", "invoice_hashes.csv")

# Tax rates
GST_RATE          = 0.18   # India — standard GST rate used by this demo
VAT_RATE          = 0.05   # UAE — standard VAT rate used by this demo

# Anomaly detection
ANOMALY_MULTIPLIER = 1.5


def _secret_or_env(name: str, default: str = "") -> str:
    """Read Streamlit Cloud secrets when available, otherwise environment variables."""
    value = os.getenv(name)
    if value is not None:
        return value

    try:
        import streamlit as st
        value = st.secrets.get(name)
        if value is not None:
            return str(value)
    except Exception:
        pass

    return default


def get_llm_config() -> dict:
    """Read LLM settings at call time so Streamlit secrets are available."""
    return {
        "enabled": _secret_or_env("LLM_REVIEW_ENABLED", "true").lower() == "true",
        "api_base": _secret_or_env("LLM_API_BASE", "https://api.groq.com/openai/v1"),
        "api_key": _secret_or_env("LLM_API_KEY", ""),
        "model": _secret_or_env("LLM_MODEL", "openai/gpt-oss-120b"),
        "timeout": int(_secret_or_env("LLM_TIMEOUT", "30")),
    }
