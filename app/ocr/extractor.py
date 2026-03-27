"""
ocr/extractor.py
Wraps Tesseract via pytesseract to extract raw text from a preprocessed image.
Set TESSERACT_CMD env var on Windows if tesseract.exe is not on PATH.
"""
import os
import numpy as np
import pytesseract

_tesseract_cmd = os.getenv("TESSERACT_CMD")
if _tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd

def extract_text(image: np.ndarray) -> str:
    """Extract raw text from a preprocessed (thresholded) image."""
    return pytesseract.image_to_string(image)