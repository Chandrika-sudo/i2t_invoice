"""utils/hash_utils.py — Hashing helpers."""
import hashlib

def md5_of_string(value: str) -> str:
    return hashlib.md5(value.encode()).hexdigest()

def md5_of_file(path: str, chunk_size: int = 8192) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()

