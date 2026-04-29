#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import Image
import numpy as np
import cv2


WINDOW_NAME = "RealSense RGB"
TOPIC_NAME = "/camera/color/image_raw"


def image_callback(msg: Image) -> None:
    if msg.encoding not in ("rgb8", "bgr8"):
        rospy.logwarn_throttle(5, f"Unsupported encoding: {msg.encoding}")
        return

    frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
    if msg.encoding == "rgb8":
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    cv2.imshow(WINDOW_NAME, frame)
    cv2.waitKey(1)


def main() -> None:
    rospy.init_node("realsense_rgb_viewer", anonymous=True)
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    rospy.Subscriber(TOPIC_NAME, Image, image_callback, queue_size=1)
    rospy.loginfo(f"Listening on topic: {TOPIC_NAME}")
    rospy.spin()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
