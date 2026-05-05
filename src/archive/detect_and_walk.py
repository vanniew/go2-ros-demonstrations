#!/usr/bin/env python3
import cv2
import message_filters
import numpy as np
import rospy
from sensor_msgs.msg import Image
from ultralytics import YOLO
from go2_controller import Go2Controller

WINDOW_NAME = "RealSense YOLO Tracker"
COLOR_TOPIC = "/camera/color/image_raw"
DEPTH_TOPIC = "/camera/aligned_depth_to_color/image_raw"
MODEL_PATH = "yolo26s.pt"
OBJECT_ID = 41
WINDOW_SIZE = (1280, 720)

model = YOLO(MODEL_PATH)
center_x = None
center_y = None


def color_to_bgr(msg: Image):
    if msg.encoding not in ("rgb8", "bgr8"):
        rospy.logwarn_throttle(5, f"Unsupported color encoding: {msg.encoding}")
        return None

    frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
    if msg.encoding == "rgb8":
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return frame


def depth_to_meters(msg: Image):
    if msg.encoding == "16UC1":
        depth = np.frombuffer(msg.data, dtype=np.uint16).reshape(msg.height, msg.width)
        return depth.astype(np.float32) * 0.001
    if msg.encoding == "32FC1":
        return np.frombuffer(msg.data, dtype=np.float32).reshape(msg.height, msg.width)

    rospy.logwarn_throttle(5, f"Unsupported depth encoding: {msg.encoding}")
    return None


def extract_target(results, depth_frame):
    global center_x, center_y

    if results is None or len(results) == 0:
        return None
    r = results[0]
    if r.boxes is None or len(r.boxes) == 0:
        return None

    best = None
    best_conf = 0.0
    for i in range(len(r.boxes)):
        cls = int(r.boxes.cls[i].item())
        if cls != OBJECT_ID:
            continue

        conf = float(r.boxes.conf[i].item())
        if conf <= best_conf:
            continue

        x, y, _, _ = r.boxes.xywh[i].tolist()
        px, py = int(round(x)), int(round(y))
        if 0 <= py < depth_frame.shape[0] and 0 <= px < depth_frame.shape[1]:
            depth_m = float(depth_frame[py, px])
        else:
            depth_m = float("nan")

        best_conf = conf
        best = (x - center_x, y - center_y, conf, depth_m, px, py)
    return best


def image_callback(color_msg: Image, depth_msg: Image) -> None:
    global center_x, center_y

    frame = color_to_bgr(color_msg)
    depth_frame = depth_to_meters(depth_msg)
    if frame is None or depth_frame is None:
        return

    if center_x is None or center_y is None:
        height, width = frame.shape[:2]
        center_x, center_y = width / 2.0, height / 2.0

    results = model(frame, verbose=False)
    detection = extract_target(results, depth_frame)
    annotated = results[0].plot()

    cv2.line(
        annotated,
        (int(center_x) - 20, int(center_y)),
        (int(center_x) + 20, int(center_y)),
        (0, 255, 0),
        2,
    )
    cv2.line(
        annotated,
        (int(center_x), int(center_y) - 20),
        (int(center_x), int(center_y) + 20),
        (0, 255, 0),
        2,
    )

    if detection is not None:
        x_err, y_err, conf, depth_m, px, py = detection
        text = (
            f"offset=({x_err:.1f}, {y_err:.1f}) "
            f"conf={conf:.2f} depth={depth_m:.2f}m"
        )
        cv2.circle(annotated, (px, py), 5, (0, 255, 255), -1)
        cv2.putText(
            annotated,
            text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )
        rospy.loginfo_throttle(1, text)

    cv2.imshow(WINDOW_NAME, annotated)
    cv2.waitKey(1)


def main() -> None:
    rospy.init_node("realsense_yolo_tracker", anonymous=True)
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, *WINDOW_SIZE)

    color_sub = message_filters.Subscriber(COLOR_TOPIC, Image)
    depth_sub = message_filters.Subscriber(DEPTH_TOPIC, Image)
    sync = message_filters.ApproximateTimeSynchronizer(
        [color_sub, depth_sub],
        queue_size=5,
        slop=0.1,
    )
    sync.registerCallback(image_callback)

    rospy.loginfo(f"Listening on topics: {COLOR_TOPIC}, {DEPTH_TOPIC}")
    rospy.spin()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
