import easyocr
import numpy as np
import cv2


''' This file is purely to test whether ocr is working. give it the path to an image and it'll check the text.'''

image = './comics_db/superboy_prime.png'
reader = easyocr.Reader(['en'], gpu=True)  # gpu=True since you've got the RTX 5070
# results = reader.readtext(image)




img = cv2.imread(image)

y, x = (1082//4), 700//5
crop_img = img[0:y, 0:x]

results = reader.readtext(crop_img, allowlist='0123456789#No.TEEN')

for bbox, text, confidence in results: 
    if confidence > 0.2:
        points = np.array(bbox, dtype=np.int32)

        cv2.polylines(crop_img, [points], isClosed=True, color=(0,0,255), thickness=4)

        bottom_left = tuple(points[1])
        cv2.putText(crop_img, text, (bottom_left[0]+10, bottom_left[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8,(0, 0, 255), 2)

        print(text, f"{confidence:0.3f}")


full_results = reader.readtext(img, allowlist='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')

for bbox, text, confidence in full_results:
    if confidence > 0.1:
        points = np.array(bbox, dtype=np.int32)

        cv2.polylines(img, [points], isClosed=True, color=(255, 0, 0), thickness=2)

        top_left = tuple(points[3])
        cv2.putText(img, text, (top_left[0], top_left[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,0,0), 2)

        print(text, f"{confidence:.3f}")



cv2.imshow('superboyprime crop', crop_img)
cv2.waitKey(0)

cv2.imshow('superboyprime', img)
cv2.waitKey(0)


cv2.destroyAllWindows()



'''ideas: 
opencv to do image analysis? 
google search to find the closest match then from there search that up in comicvine? 
'''

# from GoogleSearch import Search

# image = Image.open(path)
# output = Search(file_path=r'C:\Users\isav3\VSCode Projects\comicbook_tracker\comics_db\superboy_prime.png')

# print(output)