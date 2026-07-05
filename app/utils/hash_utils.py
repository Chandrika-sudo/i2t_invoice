import hashlib
from pathlib import Path


def file_md5(path: str) -> str:
    """Return the MD5 hex digest of a file's raw bytes."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def content_hash(text: str) -> str:
    """Return SHA-256 hex digest of a string (for deduplication of parsed text)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def invoice_fingerprint(invoice_no: str, vendor: str, total: float) -> str:
    """Stable fingerprint for duplicate detection — same as original MD5 approach."""
    raw = f"{invoice_no}{vendor}{total}"
    return hashlib.md5(raw.encode()).hexdigest()
