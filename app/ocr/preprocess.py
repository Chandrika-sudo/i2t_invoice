"""
ocr/preprocess.py
Adaptive preprocessing pipeline for invoice images.

Strategy:
  - Clean printed docs (high brightness, low noise): upscale + sharpen only
  - Scanned / photographed docs: denoise + adaptive threshold
"""

import os
import cv2
import numpy as np
from app.config.settings import PROCESSED_DIR


def _is_clean_print(gray: np.ndarray) -> bool:
    """Heuristic: bright mean + low std deviation → clean printed document."""
    return float(gray.mean()) > 180 and float(gray.std()) < 70


def preprocess_image(image_path: str) -> np.ndarray:
    """Load and preprocess an invoice image for OCR.

    Args:
        image_path: Path to the source image (JPG/PNG).
    Returns:
        Preprocessed grayscale image as numpy.ndarray.
    Raises:
        FileNotFoundError: If image_path cannot be read by OpenCV.
    """
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image at: {image_path}")

    # Upscale small images — Tesseract accuracy improves significantly at ~300 DPI
    h, w = img.shape[:2]
    if max(h, w) < 1800:
        img = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if _is_clean_print(gray):
        # Clean printed doc: sharpen only — thresholding destroys thin fonts
        kernel = np.array([[0, -1, 0],
                           [-1,  5, -1],
                           [0, -1, 0]])
        result = cv2.filter2D(gray, -1, kernel)
    else:
        # Scanned / photographed: denoise then threshold
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        result = cv2.adaptiveThreshold(
            blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 10,
        )

    output_path = os.path.join(PROCESSED_DIR, os.path.basename(image_path))
    cv2.imwrite(output_path, result)
    return result