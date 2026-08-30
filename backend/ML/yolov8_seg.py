from ultralytics import YOLO


'''The yolov8 model that will identify how many comics are in an image for multi comic image uploads!'''


def main():

    data = r'backend\ML\training_data\data.yaml'

    yolo_model = YOLO('yolov8n-obb.pt')

    results = yolo_model.train(
        data=data,
        epochs=100,
        batch=16,
        patience=8,
    )

if __name__ == "__main__":
    main()