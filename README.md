# i2t Invoice Auditor

OCR-powered invoice auditing for Indian GST and UAE VAT invoices, with an optional LLM second-opinion review.

Project Demo:
https://github.com/user-attachments/assets/a34956c9-e860-4779-845f-e2ce65038200


Live link: https://i2tinvoice-zj9qvynjbwmkelu63swhwx.streamlit.app/

## Pipeline

```text
Invoice image
    ↓
OpenCV preprocessing
    ↓
Tesseract OCR
    ↓
Rule-based invoice parser
    ↓
┌──────────────────────────────┐
│ Deterministic validation     │
│ • tax arithmetic             │
│ • vendor rules               │
│ • duplicate detection        │
│ • anomaly checks             │
└──────────────┬───────────────┘
               │
               ├──────────────┐
               ↓              ↓
          Rule results     LLM review
                              ↓
                    OCR ↔ parsed-field check
                              ↓
                    AI issues + evidence
                              │
               ┌──────────────┘
               ↓
          Final audit status
```

The LLM does not replace deterministic validation. It reviews the raw OCR text against the fields extracted by the parser and catches inconsistencies that are difficult to encode as regular expressions.

## Local setup

```bash
python -m venv venv
# Windows PowerShell
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Tesseract must also be installed locally and available on PATH. On Windows, install Tesseract separately.

Copy `.env.example` to `.env` and set your LLM key if AI review is enabled.

```bash
streamlit run streamlit_app.py
```

## LLM configuration

The application uses an OpenAI-compatible `/chat/completions` endpoint. The default configuration is Groq:

```text
LLM_REVIEW_ENABLED=true
LLM_API_BASE=https://api.groq.com/openai/v1
LLM_API_KEY=your_key
LLM_MODEL=openai/gpt-oss-120b
LLM_TIMEOUT=30
```

The provider and model can be changed without modifying the application code.

## Streamlit Community Cloud

Add this file to the repository:

```text
packages.txt
```

It contains:

```text
tesseract-ocr
```

In Streamlit Community Cloud, add these secrets:

```toml
LLM_REVIEW_ENABLED = "true"
LLM_API_BASE = "https://api.groq.com/openai/v1"
LLM_API_KEY = "your_key"
LLM_MODEL = "openai/gpt-oss-120b"
LLM_TIMEOUT = "30"
```

Never commit `.env` or an API key to GitHub.

## Tests

```bash
python -m pytest -q
```

The LLM tests mock the API call, so running the test suite does not require an API key.
