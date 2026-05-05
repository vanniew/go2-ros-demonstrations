from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient
import threading, time


class Go2Controller:
    """
    A class to control the Go2 robot's Euler angles and movement.
    """

    def __init__(self, network_interface=None):
        # Initialize the connnection to the robot
        if network_interface:
            ChannelFactoryInitialize(0, network_interface)
        else:
            ChannelFactoryInitialize(0)
        self.sport_client = SportClient()
        self.sport_client.SetTimeout(10.0)
        self.sport_client.Init()

        # Initialize multi-threading
        self._lock = threading.Lock()
        self.stop_evt = threading.Event()
        self._thread = threading.Thread(target=self._controller)
        self._thread.daemon = True

        # Set maxima
        self.MAX_YAW = 0.6
        self.MAX_PITCH = 0.6
        self.MAX_ROLL = 0.6
        self.MAX_SPEED = 0.5

        # Initialize the robot pose
        self.yaw = 0
        self.pitch = 0
        self.roll = 0
        self.vx = 0.0
        self.vy = 0.0
        self.vyaw = 0.0
        self.stand_up()
        self.set_euler(self.roll, self.pitch, self.yaw)

        # Initialize the servo thread
        self._thread.start()

    def set_euler(self, roll_rad=0, pitch_rad=0, yaw_rad=0):
        with self._lock:
            self.roll = max(min(roll_rad, self.MAX_ROLL), -self.MAX_ROLL)
            self.pitch = max(min(pitch_rad, self.MAX_PITCH), -self.MAX_PITCH)
            self.yaw = max(min(yaw_rad, self.MAX_YAW), -self.MAX_YAW)

    def get_euler(self):
        with self._lock:
            r, p, y = self.roll, self.pitch, self.yaw
        return r, p, y

    def set_speed(self, vx=0.0, vy=0.0, vyaw=0.0):
        with self._lock:
            self.vx = max(min(vx, self.MAX_SPEED), -self.MAX_SPEED)
            self.vy = max(min(vy, self.MAX_SPEED), -self.MAX_SPEED)
            self.vyaw = max(min(vyaw, self.MAX_SPEED), -self.MAX_SPEED)

    def stop_move(self):
        self.sport_client.StopMove()

    def stand_up(self):
        self.sport_client.StandUp()
        self.sport_client.BalanceStand()

    def release(self):
        # Put the robot in a neutral positon
        self.set_euler(0, 0, 0)
        self.sport_client.StopMove()
        self.sport_client.BalanceStand()
        # Stop the servo thread
        self.stop_evt.set()
        self._thread.join()

    def _controller(self, freq=10):
        while not self.stop_evt.is_set():
            with self._lock:
                r = self.roll
                p = self.pitch
                y = self.yaw
                vx = self.vx
                vy = self.vy
                vyaw = self.vyaw
            self.sport_client.Euler(roll=r, pitch=p, yaw=y)
            self.sport_client.Move(vx=vx, vy=vy, vyaw=vyaw)
            time.sleep(1 / freq)


if __name__ == "__main__":
    go2 = Go2Controller(network_interface="enp129s0")

    try:
        go2.stand_up()
        time.sleep(1)

        go2.set_speed(vx=0.2)
        time.sleep(2)

        go2.set_speed(vx=0.0, vyaw=0.4)
        time.sleep(2)

        go2.set_speed(vx=0.0, vyaw=-0.4)
        time.sleep(2)

        go2.set_speed(vx=-0.2)
        time.sleep(2)

        go2.set_speed()
        time.sleep(1)

        go2.set_euler(roll_rad=0.3)
        time.sleep(2)
        go2.set_euler(pitch_rad=0.3)
        time.sleep(2)
        go2.set_euler(yaw_rad=0.3)
        time.sleep(2)

    finally:
        go2.stop_move()
        go2.release()