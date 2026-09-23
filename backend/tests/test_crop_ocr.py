

'''script to test whether my comic detector, image cropper, and ocr works together'''
import os
import sys
import cv2

from crop_comics import ComicCropper
from ocr import extract_cover_text, extract_cover_text_with_confidence, extract_issue_number

MODEL_PATH = r'backend\ML\runs\obb\train-6\weights\best.pt'
DEFAULT_IMAGE = r'comics_db\comic_tester_2.jpeg'   # has abs batman and superman

OUT_DIR = 'test_output'


def main():
    image_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Loading model from {MODEL_PATH} ...")
    cropper = ComicCropper(MODEL_PATH, confidence_level=0.85)

    print(f"Running detection on {image_path} ...")
    crops, annotated = cropper.crop_comics(image_path)


    annotated_path = os.path.join(OUT_DIR, "annotated.jpg")
    cv2.imwrite(annotated_path, annotated)
    print(f"Saved annotated (bounding box) image -> {annotated_path}")

    print(f"\nDetected {len(crops)} comic(s).\n")

    if not crops:
        print("No comics detected -- check confidence_level or the input image.")
        return

    for i, crop in enumerate(crops):
        crop_path = os.path.join(OUT_DIR, f"crop_{i}.jpg")
        cv2.imwrite(crop_path, crop)
        height, width = crop.size().length, crop.size().width

        top_third = crop[0:height/3, 0:width/3]
        middle_third = crop[height/3:len(crop[0])-height/3, width/3:len(crop[1]-width/3)]

        joined_text = extract_cover_text(crop_path)
        raw_tokens = extract_cover_text_with_confidence(crop_path)

        print(f"--- Comic {i} ---")
        print(f"  saved crop:      {crop_path}")
        print(f"  joined OCR text: {joined_text!r}")
        print(f"  raw tokens:      {raw_tokens}")
        print()

    print(f"Check the '{OUT_DIR}' folder to visually confirm each crop is a clean, "
          f"straight, single comic cover before trusting the OCR output.")


if __name__ == '__main__':
    main()