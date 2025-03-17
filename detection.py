import os
import time

import cv2
import pandas as pd
from ultralytics import YOLO

from tracker import Tracker
from producer import produce_real_time_message

WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)
UP_LINE_Y = 294
DOWN_LINE_Y = 386
OFFSET = 7
DISTANCE = 20
VIDEO_PATH = "test.mp4"

KAFKA_BROKER = "127.0.0.1:9092"

class_names = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    4: "airplane",
    5: "bus",
    6: "lorry",
    7: "truck",
    8: "boat",
    9: "traffic light",
    10: "fire hydrant",
    11: "stop sign",
    12: "parking meter",
    13: "bench",
    14: "bird",
    15: "cat",
    16: "dog",
    17: "horse",
    18: "sheep",
    19: "cow",
    20: "elephant",
    21: "bear",
    22: "zebra",
    23: "giraffe",
    24: "backpack",
    25: "umbrella",
    26: "handbag",
    27: "tie",
    28: "suitcase",
    29: "frisbee",
    30: "skis",
    31: "snowboard",
    32: "sports ball",
    33: "kite",
    34: "baseball bat",
    35: "baseball glove",
    36: "skateboard",
    37: "surfboard",
    38: "tennis racket",
    39: "bottle",
    40: "wine glass",
    41: "cup",
    42: "fork",
    43: "knife",
    44: "spoon",
    45: "bowl",
    46: "banana",
    47: "apple",
    48: "sandwich",
    49: "orange",
    50: "broccoli",
    51: "carrot",
    52: "hot dog",
    53: "pizza",
    54: "donut",
    55: "cake",
    56: "chair",
    57: "couch",
    58: "potted plant",
    59: "bed",
    60: "dining table",
    61: "toilet",
    62: "tv",
    63: "laptop",
    64: "mouse",
    65: "remote",
    66: "keyboard",
    67: "cell phone",
    68: "microwave",
    69: "oven",
    70: "toaster",
    71: "sink",
    72: "refrigerator",
    73: "book",
    74: "clock",
    75: "vase",
    76: "scissors",
    77: "teddy bear",
    78: "hair drier",
    79: "toothbrush",
}


def check_speed(a_speed_kh, type, direction):
    if a_speed_kh > 50 and type == "lorry":

        produce_real_time_message(
            message=f"Truck going {direction} with id:{id} went with speed {a_speed_kh}Km/h ",
            topic="alerts",
            key="Alert_Message",
        )
    if a_speed_kh > 50 and type == "car":
        produce_real_time_message(
            message=f"Car going {direction} with id:{id} went with speed {a_speed_kh}Km/h ",
            topic="alerts",
            key="Alert_Message",
        )


def detect_vehicles(file_path, model=None, tracker=None):

    going_down = {}
    going_up = {}
    counter_down = []
    counter_up = []

    down = {}
    up = {}

    # Load the YOLO model
    model = YOLO("yolov8s.pt")
    tracker = Tracker()

    video_capure = cv2.VideoCapture(file_path)
    frame_count = 0

    # Create a folder to save frames
    if not os.path.exists("detected_frames"):
        os.makedirs("detected_frames")

    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter("output.avi", fourcc, 20.0, (1020, 500))

    while True:
        ret, frame = video_capure.read()
        if not ret:
            break

        frame_count = frame_count + 1
        frame = cv2.resize(frame, (1020, 500))

        results = model.predict(frame)
        df = results[0].boxes.data
        df = df.detach().cpu().numpy()
        px = pd.DataFrame(df).astype("float")

        list = []
        for _, row in px.iterrows():
            x1 = int(row[0])
            y1 = int(row[1])
            x2 = int(row[2])
            y2 = int(row[3])
            object_type = int(row[5])

            if object_type in class_names.keys():
                list.append([x1, y1, x2, y2])

        bbox_id = tracker.update(list)
        for bbox in bbox_id:
            # Corners of the box
            x3, y3, x4, y4, id = bbox

            # Center dot of the vbox
            cx = int(x3 + x4) // 2
            cy = int(y3 + y4) // 2

            # Put center dots in frame
            # cv2.circle(frame, (cx, cy), 4, RED, -1)
            # cv2.rectangle(frame, (x3, y3), (x4, y4), RED, 2)

            if UP_LINE_Y < (cy + OFFSET) and UP_LINE_Y > (cy - OFFSET):
                going_down[id] = time.time()

            if id in going_down:
                if DOWN_LINE_Y < (cy + OFFSET) and DOWN_LINE_Y > (cy - OFFSET):
                    elapsed_time = time.time() - going_down[id]
                    if counter_down.count(id) == 0:
                        counter_down.append(id)
                        a_speed_kh = (DISTANCE / elapsed_time) * 3.6
                        # Produce message if speed is high
                        check_speed(a_speed_kh, class_names.get(object_type), "down")

                        down.update(
                            {
                                id: {
                                    "time_detected": time.time(),
                                    "vehicle_type": class_names.get(object_type),
                                    "vehicle_speed": a_speed_kh,
                                }
                            }
                        )
                        cv2.circle(frame, (cx, cy), 4, RED, -1)
                        cv2.rectangle(frame, (x3, y3), (x4, y4), GREEN, 2)

                        cv2.putText(
                            frame,
                            str(id),
                            (x3, y3),
                            cv2.FONT_HERSHEY_COMPLEX,
                            0.6,
                            WHITE,
                            1,
                        )
                        cv2.putText(
                            frame,
                            str(int(a_speed_kh)) + "Km/h",
                            (x4, y4),
                            cv2.FONT_HERSHEY_COMPLEX,
                            0.8,
                            YELLOW,
                            2,
                        )

            if DOWN_LINE_Y < (cy + OFFSET) and DOWN_LINE_Y > (cy - OFFSET):
                going_up[id] = time.time()

            if id in going_up:
                if UP_LINE_Y < (cy + OFFSET) and UP_LINE_Y > (cy - OFFSET):
                    elapsed1_time = time.time() - going_up[id]
                    if counter_up.count(id) == 0:
                        counter_up.append(id)
                        a_speed_kh1 = (DISTANCE / elapsed1_time) * 3.6
                        # Produce message if speed is high
                        check_speed(a_speed_kh, class_names.get(object_type), "up")

                        up.update(
                            {
                                id: {
                                    "time_detected": time.time(),
                                    "vehicle_type": class_names.get(object_type),
                                    "vehicle_speed": a_speed_kh,
                                }
                            }
                        )

                        cv2.circle(frame, (cx, cy), 4, YELLOW, -1)
                        cv2.rectangle(frame, (x3, y3), (x4, y4), GREEN, 2)

                        cv2.putText(
                            frame,
                            str(id),
                            (x3, y3),
                            cv2.FONT_HERSHEY_COMPLEX,
                            0.6,
                            WHITE,
                            1,
                        )
                        cv2.putText(
                            frame,
                            str(int(a_speed_kh1)) + "Km/h",
                            (x4, y4),
                            cv2.FONT_HERSHEY_COMPLEX,
                            0.8,
                            YELLOW,
                            2,
                        )

            # Draw 2 green lines within 20m distance
            cv2.line(frame, (244, 294), (756, 294), GREEN, 4)
            cv2.line(frame, (73, 386), (926, 386), GREEN, 4)

            cv2.putText(
                frame,
                ("Going Down - " + str(len(counter_down))),
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                RED,
                1,
                cv2.LINE_AA,
            )
            cv2.putText(
                frame,
                ("Going Up - " + str(len(counter_up))),
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                RED,
                1,
                cv2.LINE_AA,
            )

        frame_filename = f"detected_frames/frame_{frame_count}.jpg"
        cv2.imwrite(frame_filename, frame)

        out.write(frame)

        cv2.imshow("frames", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    video_capure.release()
    out.release()
    cv2.destroyAllWindows()
    return up, down
