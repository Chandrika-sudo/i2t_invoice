import cv2
import os
from app.config.settings import PROCESSED_DIR

def preprocess_image(image_path):
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    thresh = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    filename = os.path.basename(image_path)
    output_path = os.path.join(PROCESSED_DIR, filename)
    cv2.imwrite(output_path, thresh)

    return thresh
