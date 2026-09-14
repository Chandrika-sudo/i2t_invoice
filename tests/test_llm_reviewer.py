from unittest.mock import patch

from app.llm.client import LLMError
from app.llm.reviewer import review, review_to_flags


OCR = """ACME Traders Pvt. Ltd.
Invoice No: INV-42
GSTIN: 27AAPFU0939F1ZV
Subtotal: 8474.58
GST (18%): 1525.42
TOTAL: 10000.00
"""
DATA = {
    "vendor": "ACME Traders Pvt. Ltd.",
    "invoice_no": "INV-42",
    "subtotal": 8474.58,
    "tax": 1525.42,
    "total": 10000.00,
}


@patch("app.llm.reviewer.chat_completion")
def test_clean_review(mock_call):
    mock_call.return_value = '{"flagged": false, "confidence": 0.95, "issues": []}'
    result = review(OCR, DATA)
    assert result["status"] == "PASSED"
    assert result["flagged"] is False
    assert result["issues"] == []


@patch("app.llm.reviewer.chat_completion")
def test_flagged_review(mock_call):
    mock_call.return_value = '''{
        "flagged": true,
        "confidence": 0.91,
        "issues": [{
            "type": "TOTAL_MISMATCH",
            "severity": "HIGH",
            "message": "Subtotal plus tax does not match total.",
            "evidence": "Subtotal 10000, tax 1800, total 15000"
        }]
    }'''
    result = review(OCR, DATA)
    assert result["status"] == "FLAGGED"
    assert result["issues"][0]["severity"] == "HIGH"


@patch("app.llm.reviewer.chat_completion")
def test_markdown_json_is_supported(mock_call):
    mock_call.return_value = '```json\n{"flagged": false, "confidence": 0.8, "issues": []}\n```'
    assert review(OCR, DATA)["status"] == "PASSED"


@patch("app.llm.reviewer.chat_completion")
def test_api_failure_is_not_silent(mock_call):
    mock_call.side_effect = LLMError("no API key")
    result = review(OCR, DATA)
    assert result["status"] == "UNAVAILABLE"
    assert result["error"] == "no API key"
    assert review_to_flags(OCR, DATA)[0] == []


@patch("app.llm.reviewer.chat_completion")
def test_invalid_json_returns_error_status(mock_call):
    mock_call.return_value = "not json"
    result = review(OCR, DATA)
    assert result["status"] == "ERROR"
    assert result["error"]
