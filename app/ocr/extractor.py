import shutil
import subprocess
import sys

import pytesseract


def _find_tesseract() -> None:
    """
    Auto-detect Tesseract on Windows / macOS / Linux.
    Sets pytesseract.tesseract_cmd only if the system default won't work.
    """
    # Already on PATH?
    if shutil.which("tesseract"):
        return

    candidates = []
    if sys.platform == "win32":
        import glob
        candidates = glob.glob(
            r"C:\Program Files*\Tesseract-OCR\tesseract.exe"
        ) + glob.glob(
            r"C:\Users\*\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
        )
    elif sys.platform == "darwin":
        candidates = [
            "/opt/homebrew/bin/tesseract",
            "/usr/local/bin/tesseract",
        ]

    for path in candidates:
        if shutil.which(path) or (path and __import__("os").path.isfile(path)):
            pytesseract.pytesseract.tesseract_cmd = path
            return

    # Last resort — let pytesseract raise its own clear error
    raise EnvironmentError(
        "Tesseract not found. Install it and ensure it is on your PATH.\n"
        "  Linux : sudo apt install tesseract-ocr\n"
        "  macOS : brew install tesseract\n"
        "  Windows: https://github.com/UB-Mannheim/tesseract/wiki"
    )


_find_tesseract()


def extract_text(image) -> str:
    """
    Run Tesseract OCR on a pre-processed numpy image.

    Uses --psm 6 (assume a uniform block of text) which performs well on
    structured invoice layouts. Falls back to --psm 4 on error.
    """
    config = r"--oem 3 --psm 6"
    try:
        text = pytesseract.image_to_string(image, config=config)
    except pytesseract.pytesseract.TesseractError:
        text = pytesseract.image_to_string(image, config=r"--oem 3 --psm 4")
    return text
