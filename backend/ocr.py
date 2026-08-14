"""
Pulls raw text off a photographed comic cover so we have something to
search ComicVine with. This is deliberately rough — the user picks the
right result from a shortlist of thumbnails, so OCR just needs to get
close enough (usually the series title in the logo is what comes through
cleanest).
"""
from PIL import Image
import pytesseract


def extract_cover_text(image_path: str) -> str:
    img = Image.open(image_path).convert("RGB")
    raw = pytesseract.image_to_string(img)
    # collapse whitespace, keep it short — long OCR noise makes a worse query
    words = [w for w in raw.split() if len(w) > 1]
    return " ".join(words[:12])
