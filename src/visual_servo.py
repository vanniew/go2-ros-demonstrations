import time
import cv2
from src.euler_controller import Go2EulerServo
from src.yolo_tracker import Go2YOLOTracker

class Go2VisualServo:
    """
    Continuous P visual servo using tracker-provided pixel offsets:
      detection = (x_err_px, y_err_px, conf)
    """
    def __init__(
        self,
        ctrl_freq=10,
        track_freq=10,
        Kp_yaw=0.001,
        Kp_pitch=0.001,
        conf_min=0.0,
        object_id=41,
        network_interface=None,
    ):
        self.ctrl_freq = ctrl_freq
        self.track_freq = track_freq
        self.Kp_yaw = Kp_yaw
        self.Kp_pitch = Kp_pitch
        self.conf_min = conf_min

        self.servo = Go2EulerServo(network_interface=network_interface)
        self.tracker = Go2YOLOTracker(
            object_id=object_id,
            network_interface=network_interface,
        )
        self.yaw = 0
        self.pitch = 0
        
        self.last_detection = None

    def _compute_euler_cmd(self, detection):
        """
        detection: (x_err_px, y_err_px, conf)
        returns: (roll, pitch, yaw) in radians
        """
    
        now = time.time()
    
        # 1. Update last detection if a new one exists
        if detection is not None:
            self.last_detection = {
                "detection": detection,
                "timestamp": now
            }
    
        # 2. Resolve current valid detection
        if self.last_detection is None:
            return None
    
        if now - self.last_detection["timestamp"] > 0.5:
            self.last_detection = None
            return None
    
        x_err, y_err, conf = self.last_detection["detection"]
    
        # 3. Confidence gating
        if conf < self.conf_min:
            return None
    
        # 4. P control
        yaw_cmd   = -self.Kp_yaw * x_err
        pitch_cmd =  self.Kp_pitch * y_err
        roll_cmd  = 0.0
    
        return roll_cmd, pitch_cmd, yaw_cmd

    def start(self):
        while True:
            detection = self.tracker.inference()
            frame = self.tracker.visualize()
            if frame is not None:
                cv2.imshow("YOLO Tracker", frame)

            if cv2.waitKey(1) == 27:
                cv2.destroyAllWindows()
                break

            cmd = self._compute_euler_cmd(detection)
            if cmd is not None:
                self.yaw += cmd[2]
                self.yaw = max(-0.6, min(0.6, self.yaw))
                self.pitch += cmd[1]
                self.pitch = max(-0.6, min(0.6, self.pitch))

            print(f"\rPitch: {self.pitch}, Yaw: {self.yaw}                     ", end="")
            if self.pitch is not None and self.yaw is not None:
                self.servo.set_euler(0, self.pitch, self.yaw)

            time.sleep(1 / self.track_freq)

    def stop(self):
        cv2.destroyAllWindows()
        self.servo.release()
 