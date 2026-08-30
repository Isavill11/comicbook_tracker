from ultralytics import YOLO
import numpy as np

import cv2




def draw_bounding_boxes(image, boxes, classes, confidences, class_names=None) -> None:

    for box, cls, conf in zip(boxes, classes, confidences):
        # box comes in as a tensor of shape (4, 2) -> the 4 corner (x, y) points.
        # Move to CPU + numpy + int32 so cv2 can use it.
        points = box.cpu().numpy().astype(np.int32)
        points = points.reshape((-1, 1, 2))  # shape cv2.polylines expects

        # Draw the rotated box outline
        cv2.polylines(image, [points], isClosed=True, color=(0, 255, 0), thickness=2)

        # Build a label like "cover 0.94"
        cls_id = int(cls.item())
        label = f"{class_names[cls_id] if class_names else cls_id} {conf.item():.2f}"

        # Anchor the label at the top-left-most corner of the box
        label_pos = tuple(points[0][0])
        cv2.putText(
            image, label, label_pos,
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA
        )

    


model = YOLO(r'backend\ML\runs\obb\train-6\weights\best.pt')

image_path = r'comics_db\comic_tester_2.jpeg'
results = model(image_path)

image = cv2.imread(image_path)


for result in results: 
    boxes = result.obb.xyxyxyxy
    classes = result.obb.cls
    confidence = result.obb.conf
    class_name = result.names


    draw_bounding_boxes(image, boxes, classes, confidence, class_name)

cv2.imshow('OBB Detection', image)
cv2.waitKey(0)
cv2.destroyAllWindows()

cv2.imwrite('comics_db/comic_tester_2_output.jpeg', image)



    



