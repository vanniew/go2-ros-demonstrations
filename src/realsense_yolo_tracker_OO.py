"""
This script launches a ROS node that subscribes to the color and depth images from the RealSense camera and runs YOLO on the RGB image.
It overlays the target offset plus measured depth on the image. We recommend to run the script in a docker container that has the unitree SDK2 and ROS Noetic Installed. 

You can test the YOLO Tracker by running the following command:
```bash
python3 realsense_yolo_tracker_OO.py
```
"""


#!/usr/bin/env python3
import cv2
import message_filters
import numpy as np
import rospy
from sensor_msgs.msg import Image
from ultralytics import YOLO


class RealSenseYOLOTracker:
    def __init__(
        self,
        object_id=41,
        model_path="yolo26s.pt",
        color_topic="/camera/color/image_raw",
        depth_topic="/camera/aligned_depth_to_color/image_raw",
        window_name="RealSense YOLO Tracker",
    ):
        self.object_id = object_id
        self.color_topic = color_topic
        self.depth_topic = depth_topic
        self.window_name = window_name
        self.model = YOLO(model_path)

        self.center_x = None
        self.center_y = None
        self.frame = None
        self.depth = None
        self.results = None
        self.detection = None
        self.annotated_frame = None

        self.color_sub = None
        self.depth_sub = None
        self.sync = None

    def connect(self):
        self.color_sub = message_filters.Subscriber(self.color_topic, Image)
        self.depth_sub = message_filters.Subscriber(self.depth_topic, Image)
        self.sync = message_filters.ApproximateTimeSynchronizer(
            [self.color_sub, self.depth_sub],
            queue_size=5,
            slop=0.1,
        )
        self.sync.registerCallback(self._image_callback)

    def disconnect(self):
        self.color_sub.sub.unregister()
        self.depth_sub.sub.unregister()
        cv2.destroyAllWindows()

    def inference(self):
        if self.frame is None or self.depth is None:
            return None

        self.results = self.model(self.frame, verbose=False)
        self.detection = self._extract_target()
        self.annotated_frame = self.results[0].plot()
        if self.detection is not None:
            x_err, y_err, conf, depth_m, px, py = self.detection
            print(f"offset=({x_err:.1f}, {y_err:.1f}), conf={conf:.2f}, depth={depth_m:.2f}m, pixel=({px},{py})")

        return self.detection

    def visualize(self):
        if self.annotated_frame is None:
            return None

        frame = self.annotated_frame.copy()
        cv2.line(
            frame,
            (int(self.center_x) - 20, int(self.center_y)),
            (int(self.center_x) + 20, int(self.center_y)),
            (0, 255, 0),
            2,
        )
        cv2.line(
            frame,
            (int(self.center_x), int(self.center_y) - 20),
            (int(self.center_x), int(self.center_y) + 20),
            (0, 255, 0),
            2,
        )

        if self.detection is not None:
            x_err, y_err, conf, depth_m, px, py = self.detection
            text = (
                f"offset=({x_err:.1f}, {y_err:.1f}) "
                f"conf={conf:.2f} depth={depth_m:.2f}m"
            )
            cv2.circle(frame, (px, py), 5, (0, 255, 255), -1)
            cv2.putText(
                frame,
                text,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
            )

        return frame

    def _image_callback(self, color_msg, depth_msg):
        self.frame = self._color_to_bgr(color_msg)
        self.depth = self._depth_to_meters(depth_msg)
        height, width = self.frame.shape[:2]
        self.center_x = width / 2.0
        self.center_y = height / 2.0

    def _extract_target(self):
        boxes = self.results[0].boxes
        best = None
        best_conf = 0.0

        for i in range(len(boxes)):
            cls = int(boxes.cls[i].item())
            conf = float(boxes.conf[i].item())
            if cls != self.object_id or conf <= best_conf:
                continue

            x, y, _, _ = boxes.xywh[i].tolist()
            px, py = int(round(x)), int(round(y))
            depth_m = float(self.depth[py, px])
            best = (x - self.center_x, y - self.center_y, conf, depth_m, px, py)
            best_conf = conf

        return best

    @staticmethod
    def _color_to_bgr(msg):
        frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
        if msg.encoding == "rgb8":
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame

    @staticmethod
    def _depth_to_meters(msg):
        if msg.encoding == "32FC1":
            return np.frombuffer(msg.data, dtype=np.float32).reshape(msg.height, msg.width)

        depth = np.frombuffer(msg.data, dtype=np.uint16).reshape(msg.height, msg.width)
        return depth.astype(np.float32) * 0.001


def main():
    rospy.init_node("realsense_yolo_tracker_oo", anonymous=True)
    tracker = RealSenseYOLOTracker()
    tracker.connect()

    rate = rospy.Rate(10)
    while not rospy.is_shutdown():
        tracker.inference()
        frame = tracker.visualize()
        if frame is not None:
            cv2.imshow(tracker.window_name, frame)
            cv2.waitKey(1)
        rate.sleep()

    tracker.disconnect()


if __name__ == "__main__":
    main()
