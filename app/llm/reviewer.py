"""LLM second-opinion review of OCR text and parsed invoice fields."""

from __future__ import annotations

import json
import re
from typing import TypedDict

from app.llm.client import LLMError, chat_completion
from app.llm.prompts import SYSTEM_PROMPT
from app.utils.logger import get_logger

logger = get_logger("llm.reviewer")

MAX_OCR_CHARS = 10000


class ReviewIssue(TypedDict):
    type: str
    severity: str
    message: str
    evidence: str


class LLMReviewResult(TypedDict):
    status: str  # PASSED, FLAGGED, UNAVAILABLE, ERROR
    flagged: bool
    confidence: float
    issues: list[ReviewIssue]
    error: str | None


def _truncate_ocr(text: str) -> str:
    """Keep both the header and totals area when OCR is unusually long."""
    text = text.strip()
    if len(text) <= MAX_OCR_CHARS:
        return text

    head = MAX_OCR_CHARS * 3 // 5
    tail = MAX_OCR_CHARS - head
    return (
        text[:head]
        + "\n\n...[middle of OCR omitted for prompt size]...\n\n"
        + text[-tail:]
    )


def _extract_json(raw: str) -> dict:
    """Parse plain JSON or JSON wrapped in a markdown code fence."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
        if not isinstance(value, dict):
            raise ValueError("LLM response is not a JSON object")
        return value
    except json.JSONDecodeError:
        # Last-resort extraction if a provider adds a short sentence around JSON.
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        value = json.loads(cleaned[start : end + 1])
        if not isinstance(value, dict):
            raise ValueError("LLM response is not a JSON object")
        return value


def _normalise_result(data: dict) -> LLMReviewResult:
    flagged = bool(data.get("flagged", False))
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    raw_issues = data.get("issues", [])
    if not isinstance(raw_issues, list):
        raw_issues = []

    issues: list[ReviewIssue] = []
    for item in raw_issues:
        if isinstance(item, str):
            message = item.strip()
            if message:
                issues.append({
                    "type": "AI_REVIEW",
                    "severity": "MEDIUM",
                    "message": message,
                    "evidence": "",
                })
            continue

        if not isinstance(item, dict):
            continue

        message = str(item.get("message", "")).strip()
        if not message:
            continue

        severity = str(item.get("severity", "MEDIUM")).upper()
        if severity not in {"LOW", "MEDIUM", "HIGH"}:
            severity = "MEDIUM"

        issues.append({
            "type": str(item.get("type", "AI_REVIEW")).upper(),
            "severity": severity,
            "message": message,
            "evidence": str(item.get("evidence", "")).strip(),
        })

    if flagged and not issues:
        issues.append({
            "type": "AI_REVIEW",
            "severity": "MEDIUM",
            "message": "The AI reviewer flagged the invoice but returned no specific issue.",
            "evidence": "",
        })

    return {
        "status": "FLAGGED" if flagged else "PASSED",
        "flagged": flagged,
        "confidence": confidence,
        "issues": issues,
        "error": None,
    }


def review(raw_text: str, parsed_data: dict) -> LLMReviewResult:
    """Review OCR text against parser output. Never raises to the audit pipeline."""
    if not raw_text.strip():
        return {
            "status": "ERROR",
            "flagged": False,
            "confidence": 0.0,
            "issues": [],
            "error": "OCR returned no text",
        }

    user_prompt = (
        "RAW OCR TEXT:\n"
        f"{_truncate_ocr(raw_text)}\n\n"
        "FIELDS EXTRACTED BY RULE-BASED PARSER:\n"
        f"{json.dumps(parsed_data, indent=2, default=str)}"
    )

    try:
        reply = chat_completion(SYSTEM_PROMPT, user_prompt, temperature=0.0)
        return _normalise_result(_extract_json(reply))
    except LLMError as exc:
        logger.warning("LLM review unavailable: %s", exc)
        return {
            "status": "UNAVAILABLE",
            "flagged": False,
            "confidence": 0.0,
            "issues": [],
            "error": str(exc),
        }
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Could not parse LLM review response: %s", exc)
        return {
            "status": "ERROR",
            "flagged": False,
            "confidence": 0.0,
            "issues": [],
            "error": f"Unparseable LLM response: {exc}",
        }


def review_to_flags(raw_text: str, parsed_data: dict) -> tuple[list[str], LLMReviewResult]:
    """Return UI-friendly flags plus the complete AI review result."""
    result = review(raw_text, parsed_data)
    flags: list[str] = []

    for issue in result["issues"]:
        evidence = f" Evidence: {issue['evidence']}" if issue["evidence"] else ""
        flags.append(
            f"🤖 AI review [{issue['severity']}]: {issue['message']}{evidence}"
        )

    return flags, result
