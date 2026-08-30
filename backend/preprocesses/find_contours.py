import cv2
import numpy as np
import requests


image = cv2.imread(r'comics_db\abs_superman.jpeg')
# gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)



# import requests

# response = requests.post(
#     'https://api.remove.bg/v1.0/removebg',
#     files={'image_file': open(r'comics_db\abs_superman.jpeg', 'rb')},
#     data={'size': 'auto'},
#     headers={'X-Api-Key': 'YUo93tFt7mKeD8Av3P8wGZfq'},
# )
# if response.status_code == requests.codes.ok:
#     with open('no-bg.png', 'wb') as out:
#         out.write(response.content)
# else:
#     print("Error:", response.status_code, response.text)






# # heavy blur suppresses interior art/text edges, keeps the strong outer border
# blurred = cv2.GaussianBlur(gray, (9, 9), 0)
# edges = cv2.Canny(blurred, 30, 100)


# kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (12, 12))

# edges = cv2.morphologyEx(image, cv2.MORPH_BLACKHAT, kernel)




# cv2.imshow('warping and edging', edges)

# cv2.waitKey(0)

# # close small gaps in the comic's outer edge so it forms one continuous loop
# kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (12, 12))
# closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)


# contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)


# cv2.imshow('boxes', closed)

# cv2.waitKey(0)

# # keep only large, roughly-quadrilateral contours (i.e. actual comics, not noise)
# min_area = 0.5 * image.shape[0] * image.shape[1]  # tune this


# comic_boxes = []
# for c in contours:
#     area = cv2.contourArea(c)
#     if area < min_area:
#         continue
#     peri = cv2.arcLength(c, True)
#     approx = cv2.approxPolyDP(c, 0.02 * peri, True)
#     if len(approx) == 4:  # roughly rectangular
#         rect = cv2.minAreaRect(c)
#         box = cv2.boxPoints(rect)
#         comic_boxes.append(np.intp(box))

# for box in comic_boxes:
#     cv2.drawContours(image, [box], 0, (0, 0, 255), 2)

# cv2.imshow('debug_boxes.jpg', image)
# cv2.waitKey(0)
# print(f"found {len(comic_boxes)} comic-shaped regions")


# '''contour detection using moments + contour perimeter'''




# ret,thresh = cv2.threshold(image,127,255,0)
# contours,hierarchy = cv2.findContours(thresh, 1, 2)
# cnt = contours[0]


# rect = cv2.minAreaRect(cnt)
# box = cv2.boxPoints(rect)
# box = np.int8(box)
# cv2.drawContours(image,[box],0,(0,0,255),2)
