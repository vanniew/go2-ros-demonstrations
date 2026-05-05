from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient
from ultralytics import YOLO
import cv2
import numpy as np
import threading

class Go2YOLOTracker:
    
    def __init__(self, object_id=0,  network_interface=None):
        # Initialize arguments
        self.object_id = object_id

        # Initialize frame dimensions
        self.height, self.width = None, None
        self.center_x, self.center_y = None, None

        # Initialize the connnection to the robot
        if network_interface:
            ChannelFactoryInitialize(0, network_interface)
        else:
            ChannelFactoryInitialize(0)
        self.video_client = VideoClient()
        self.video_client.SetTimeout(3.0)
        self.video_client.Init()

        # Initialize the YOLO model
        self.model = YOLO("yolo26s.pt")

        # Keep the latest detection
        self._latest_target_offset = None
        self._latest_annotated_frame = None

    def _extract_target_offset(self, results):
        """
        Return (cx, cy) of the best (highest confidence) object detection for class_id, or None.
        results: single-frame result from model(frame); use results[0].boxes.
        """
        if results is None or len(results) == 0:
            return None
        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return None
        boxes = r.boxes
        best = None
        best_conf = 0.0
        for i in range(len(boxes)):
            cls = int(boxes.cls[i].item())
            if cls != self.object_id:
                continue
            conf = float(boxes.conf[i].item())
            if conf > best_conf:
                best_conf = conf
                x, y, _, _ = boxes.xywh[i].tolist()
                best = (x - self.center_x, y - self.center_y, conf)
        return best


    def inference(self):
        code, data = self.video_client.GetImageSample()
        if code != 0:
            return None
        frame = np.frombuffer(bytes(data), dtype=np.uint8)
        frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
        if frame is None:
            return None

        # Initialize frame dimensions
        if self.height is None or self.width is None:
            self.height, self.width = frame.shape[:2]
            self.center_x, self.center_y = self.width / 2.0, self.height / 2.0
        # Get the target position
        results = self.model(frame,verbose=False)
        self._latest_target_offset = self._extract_target_offset(results)
        self._latest_annotated_frame = results[0].plot()

        return self._latest_target_offset

    def visualize(self):
        if self._latest_annotated_frame is None:
            print("Run inference before visualize")
            return None
        cv2.line(
            self._latest_annotated_frame,
            (int(self.center_x) - 20, int(self.center_y)),
            (int(self.center_x) + 20, int(self.center_y)),
            (0, 255, 0),
            2,
        )
        cv2.line(
            self._latest_annotated_frame,
            (int(self.center_x), int(self.center_y) - 20),
            (int(self.center_x), int(self.center_y) + 20),
            (0, 255, 0),
            2,
        )
        return self._latest_annotated_frame