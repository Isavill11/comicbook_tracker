from ultralytics import YOLO
import cv2
import numpy as np


class ComicCropper:
    def __init__(self, model_path: str, confidence_level: float = 0.85):
        self.model = YOLO(model_path)
        self.confidence_level = confidence_level

    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        '''sort the corners top left to bottom left'''
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # top-left
        rect[2] = pts[np.argmax(s)]  # bottom-right

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # top-right
        rect[3] = pts[np.argmax(diff)]  # bottom-left
        return rect

    def warp_crop(self, image: np.ndarray, points: np.ndarray) -> np.ndarray:
        '''This will rotate the image to be straight if the comic is crooked'''
        rect = self.order_points(points)
        (tl, tr, br, bl) = rect

        width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
        height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))

        dst = np.array([
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1],
            [0, height - 1]
        ], dtype=np.float32)

        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(image, M, (width, height))

    @staticmethod
    def draw_bounding_boxes(image, boxes, classes, confidences, class_names=None) -> None:
        for box, cls, conf in zip(boxes, classes, confidences):
            points = box.cpu().numpy().astype(np.int32)
            points = points.reshape((-1, 1, 2))

            cv2.polylines(image, [points], isClosed=True, color=(0, 255, 0), thickness=2)

            cls_id = int(cls.item())
            label = f"{class_names[cls_id] if class_names else cls_id} {conf.item():.2f}"
            label_pos = tuple(points[0][0])
            cv2.putText(
                image, label, label_pos,
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA
            )

    def crop_comics(self, image_path: str):
        '''Returns a list of cropped images the model detects, and an annotated image for reference.'''
        results = self.model(image_path, conf=self.confidence_level)

        original = cv2.imread(image_path)
        display = original.copy()  # copy so the drawn lines don't persist in the final crops

        crops = []
        for result in results:
            boxes = result.obb.xyxyxyxy
            classes = result.obb.cls
            confidence = result.obb.conf
            class_names = result.names

            self.draw_bounding_boxes(display, boxes, classes, confidence, class_names)

            for box in boxes:
                points = box.cpu().numpy().astype(np.float32)
                crop = self.warp_crop(original, points)
                crops.append(crop)

        return crops, display

    def display_cropped_images(self) -> None: 
        crops, image = self.crop_comics(r'comics_db\comic_tester_2.jpeg')

        cv2.imshow('annotated image', image)
        cv2.waitKey(0)

        for i, img in enumerate(crops):
            print(f"showing crop {i + 1}/{len(crops)}")
            cv2.namedWindow('cropped image', cv2.WINDOW_NORMAL)
            cv2.imshow('cropped image', img)
            cv2.waitKey(0)

        cv2.destroyAllWindows()


# if __name__ == '__main__':
#     cropper = ComicCropper(r'backend\ML\runs\obb\train-6\weights\best.pt', confidence_level=0.85)
#     crops, image = cropper.crop_comics(r'comics_db\comic_tester_2.jpeg')

#     cv2.imshow('annotated image', image)
#     cv2.waitKey(0)

#     for i, img in enumerate(crops):
#         print(f"showing crop {i + 1}/{len(crops)}")
#         cv2.namedWindow('cropped image', cv2.WINDOW_NORMAL)
#         cv2.imshow('cropped image', img)
#         cv2.waitKey(0)

#     cv2.destroyAllWindows()