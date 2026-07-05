import os
import shutil
from pathlib import Path
from typing import List


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".pdf"}


def is_supported(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS


def collect_invoices(directory: str) -> List[str]:
    """Recursively collect all supported invoice files in a directory."""
    files = []
    for root, _, filenames in os.walk(directory):
        for fname in filenames:
            full = os.path.join(root, fname)
            if is_supported(full):
                files.append(full)
    return sorted(files)


def ensure_dir(path: str) -> str:
    """Create directory (and parents) if it doesn't exist. Returns the path."""
    os.makedirs(path, exist_ok=True)
    return path


def safe_copy(src: str, dst_dir: str) -> str:
    """Copy src to dst_dir, returning the destination path."""
    ensure_dir(dst_dir)
    dst = os.path.join(dst_dir, os.path.basename(src))
    shutil.copy2(src, dst)
    return dst


def file_size_kb(path: str) -> float:
    return os.path.getsize(path) / 1024
