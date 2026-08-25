"""
Pulls raw text off a photographed comic cover so we have something to
search ComicVine with. This is deliberately rough — the user picks the
right result from a shortlist of thumbnails, so OCR just needs to get
close enough (usually the series title in the logo is what comes through
cleanest).
"""




import easyocr
import numpy as np
import cv2






def extract_cover_text(image_path: str) -> str:
    
    ''' return text extracted from image (str)'''
    image = image_path
    reader = easyocr.Reader(['en'], gpu=True)  # gpu=True since you've got the RTX 5070
    extracted_text = []

    results = reader.readtext(image, allowlist='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')

    for bbox, text, confidence in results:
        if confidence > 0.1:
            extracted_text.append((text, confidence))

    return extracted_text

def extract_issue_number(image_path:str, roi:list):
    '''return numbers extracted from the roi of a comic'''
    
    image = image_path
    crop_img = cv2.imread(image)
    crop_img = crop_img[0:roi[0], 0:roi[1]]
    reader = easyocr.Reader(['en'], gpu=True)
    extracted_integers = []

    int_results = reader.readtext(crop_img, allowlist='1234567890#')

    for bbox, text, confidence in int_results: 
        if confidence > 0.2:
            extracted_integers.append((text, confidence))

    
