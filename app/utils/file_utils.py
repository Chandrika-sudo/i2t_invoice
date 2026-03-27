"""utils/file_utils.py — File and directory helpers."""
import os, shutil
from pathlib import Path

def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path

def is_supported_image(path: str) -> bool:
    return Path(path).suffix.lower() in {".jpg", ".jpeg", ".png"}

def safe_copy(src: str, dst_dir: str) -> str:
    ensure_dir(dst_dir)
    dst = os.path.join(dst_dir, os.path.basename(src))
    shutil.copy2(src, dst)
    return dst