"""
The first script is tailored to pull only text from the comic book covers and the second will hopefully pull the issue number.
"""

from typing import List, Tuple, Optional

import easyocr
import numpy as np
import cv2

_reader = easyocr.Reader(['en'], gpu=True)


def extract_cover_text(image_path: str, min_confidence: float = 0.1) -> Optional[str]:

    results = _reader.readtext(
        image_path,
        allowlist='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890 '
    )

    tokens = [text for (bbox, text, confidence) in results if confidence > min_confidence]

    if not tokens:
        return None

    return " ".join(tokens).strip()


def extract_cover_text_with_confidence(image_path: str, min_confidence: float = 0.1) -> List[Tuple[str, float]]:
    
    results = _reader.readtext(
        image_path,
        allowlist='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890 '
    )
    return [(text, confidence) for (bbox, text, confidence) in results if confidence > min_confidence]


def extract_issue_number(image_path: str, roi: List[int]) -> List[Tuple[str, float]]:

    
    crop_img = cv2.imread(image_path)
    crop_img = crop_img[0:roi[0], 0:roi[1]]

    results = _reader.readtext(crop_img, allowlist='1234567890#')

    return [(text, confidence) for (bbox, text, confidence) in results if confidence > 0.2]


if __name__ == '__main__':
    image = r'test_output\crop_2.jpg'
    print(extract_cover_text(image))