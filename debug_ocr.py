# debug_ocr.py  — run once to see raw OCR output, then delete
import cv2
import numpy as np
from app.ocr.preprocess import preprocess_image
from app.ocr.extractor import extract_text

image_path = r"data\raw_invoices\sample2.jpg"

processed = preprocess_image(image_path)
text = extract_text(processed)

print("=" * 60)
print(repr(text))          # shows every \n, \t, space exactly
print("=" * 60)
print(text)                # human-readable version