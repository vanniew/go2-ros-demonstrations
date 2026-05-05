#!/usr/bin/env python3
import math

import cv2
import rospy
import time

from go2_controller import Go2Controller
from realsense_yolo_tracker_OO import RealSenseYOLOTracker


OBJECT_ID = 41
TARGET_DISTANCE_M = 0.7
MAX_DISTANCE_M = 3
MIN_DISTANCE_M = 0
MAX_SPEED = 0.2
MAX_YAW_RATE = 0.3
KP_FORWARD = 0.50
KP_YAW = 0.004

UNITREE_NIC = "enp129s0"


def clamp(value, low, high):
    return max(low, min(high, value))

class DetectionMemory:
    def __init__(self, lost_timeout_s=0.4, alpha_depth=0.4, alpha_x=0.4):
        self.lost_timeout_s = lost_timeout_s
        self.alpha_depth = alpha_depth
        self.alpha_x = alpha_x

        self.last_detection = None
        self.last_seen_time = None

    def detection_is_valid(self, detection):
        if detection is None:
            return False

        _, _, _, depth_m, _, _ = detection
        return math.isfinite(depth_m) and depth_m < MAX_DISTANCE_M

    def update(self, detection):
        now = time.time()

        if self.detection_is_valid(detection):
            x_err, y_err, conf, depth_m, bbox, class_id = detection

            if self.last_detection is not None:
                old_x_err, old_y_err, old_conf, old_depth_m, old_bbox, old_class_id = self.last_detection

                # Smooth the two most important unstable signals
                x_err = self.alpha_x * x_err + (1 - self.alpha_x) * old_x_err
                depth_m = self.alpha_depth * depth_m + (1 - self.alpha_depth) * old_depth_m

                detection = (x_err, y_err, conf, depth_m, bbox, class_id)

            self.last_detection = detection
            self.last_seen_time = now
            return detection

        # No detection this frame, but recently seen: reuse last detection
        if self.last_seen_time is not None:
            if now - self.last_seen_time < self.lost_timeout_s:
                return self.last_detection

        # Lost for too long
        self.last_detection = None
        self.last_seen_time = None
        return None


def compute_walk_command(detection):
    if detection is None:
         return 0.0, 0.0, 0.0

    x_err, _, _, depth_m, _, _ = detection
    # vx = clamp(KP_FORWARD * (depth_m - TARGET_DISTANCE_M), -MAX_SPEED, MAX_SPEED) # Move backwards if object is very close
    vx = clamp(KP_FORWARD * (depth_m - TARGET_DISTANCE_M), 0.0, MAX_SPEED) # Stop if object is at target range
    vy= 0.0
    vyaw = clamp(-KP_YAW * x_err, -MAX_YAW_RATE, MAX_YAW_RATE)
    # return vx, 0.0, vyaw
    print(f"vx={vx}, vy={vy}, vyaw={vyaw}")

    return vx, 0.0, vyaw

def main():
    rospy.init_node("detect_and_walk_oo", anonymous=True)

    tracker = RealSenseYOLOTracker(object_id=OBJECT_ID)
    go2 = Go2Controller(network_interface=UNITREE_NIC)

    detection_memory = DetectionMemory()

    tracker.connect()
    go2.stand_up()

    rate = rospy.Rate(10)
    try:
        while not rospy.is_shutdown():
            raw_detection = tracker.inference()
            detection = detection_memory.update(raw_detection)

            frame = tracker.visualize()
            
            vx, vy, vyaw = compute_walk_command(detection)
            go2.set_speed(vx, vy, vyaw)

            if frame is not None:
                cv2.imshow(tracker.window_name, frame)
                if cv2.waitKey(1) == 27:
                    break

            rate.sleep()
    finally:
        go2.stop_move()
        time.sleep(1)
        go2.release()
        tracker.disconnect()


if __name__ == "__main__":
    main()
