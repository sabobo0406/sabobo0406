"""
移動ベース制御モジュール

メカナムホイールベースを制御し、全方向移動を実現する。
前後左右移動、回転、斜め移動が可能。
"""

import time
import math
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from loguru import logger

try:
    import serial
except ImportError:
    serial = None


class BaseState(Enum):
    STOPPED = "stopped"
    MOVING = "moving"
    ROTATING = "rotating"
    ERROR = "error"


@dataclass
class Velocity:
    """ロボットの速度指令"""
    linear_x: float = 0.0   # 前後 (m/s)
    linear_y: float = 0.0   # 左右 (m/s)
    angular_z: float = 0.0  # 回転 (rad/s)


@dataclass
class Pose:
    """ロボットの位置姿勢"""
    x: float = 0.0       # メートル
    y: float = 0.0       # メートル
    theta: float = 0.0   # ラジアン


@dataclass
class BaseConfig:
    serial_port: str = "/dev/ttyUSB1"
    baud_rate: int = 115200
    wheel_diameter: float = 0.1
    wheel_base: float = 0.4
    max_linear_speed: float = 0.5
    max_angular_speed: float = 1.0
    pid_kp: float = 1.0
    pid_ki: float = 0.1
    pid_kd: float = 0.05


class MobileBaseController:
    """メカナムホイール移動ベースの制御クラス"""

    def __init__(self, config: Optional[BaseConfig] = None):
        self.config = config or BaseConfig()
        self.state = BaseState.STOPPED
        self.current_velocity = Velocity()
        self.odometry = Pose()
        self._serial: Optional[serial.Serial] = None
        self._lock = threading.Lock()
        self._simulation_mode = serial is None
        self._odom_thread: Optional[threading.Thread] = None
        self._running = False
        logger.info(f"MobileBaseController initialized (simulation={self._simulation_mode})")

    def connect(self) -> bool:
        """移動ベースに接続する"""
        if self._simulation_mode:
            logger.info("[SIM] Mobile base connected (simulation)")
            self.state = BaseState.STOPPED
            self._start_odometry()
            return True

        try:
            self._serial = serial.Serial(
                port=self.config.serial_port,
                baudrate=self.config.baud_rate,
                timeout=1.0,
            )
            time.sleep(2)
            self.state = BaseState.STOPPED
            self._start_odometry()
            logger.info(f"Mobile base connected on {self.config.serial_port}")
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to connect mobile base: {e}")
            self.state = BaseState.ERROR
            return False

    def disconnect(self):
        """接続を切断する"""
        self.stop()
        self._running = False
        if self._odom_thread:
            self._odom_thread.join(timeout=2)
        if self._serial and self._serial.is_open:
            self._serial.close()
        logger.info("Mobile base disconnected")

    def _send_command(self, command: str) -> Optional[str]:
        """シリアルコマンドを送信する"""
        with self._lock:
            if self._simulation_mode:
                logger.debug(f"[SIM] Base command: {command}")
                return "OK"
            if not self._serial or not self._serial.is_open:
                return None
            self._serial.write(f"{command}\n".encode())
            return self._serial.readline().decode().strip()

    def _clamp_velocity(self, velocity: Velocity) -> Velocity:
        """速度を制限範囲内に収める"""
        linear_speed = math.sqrt(velocity.linear_x ** 2 + velocity.linear_y ** 2)
        if linear_speed > self.config.max_linear_speed:
            scale = self.config.max_linear_speed / linear_speed
            velocity.linear_x *= scale
            velocity.linear_y *= scale

        velocity.angular_z = max(
            -self.config.max_angular_speed,
            min(self.config.max_angular_speed, velocity.angular_z),
        )
        return velocity

    def _start_odometry(self):
        """オドメトリ更新スレッドを開始する"""
        self._running = True
        self._odom_thread = threading.Thread(target=self._odometry_loop, daemon=True)
        self._odom_thread.start()

    def _odometry_loop(self):
        """オドメトリを定期更新する"""
        dt = 0.05  # 50ms
        while self._running:
            vel = self.current_velocity
            # 簡易オドメトリ更新
            self.odometry.x += (
                vel.linear_x * math.cos(self.odometry.theta)
                - vel.linear_y * math.sin(self.odometry.theta)
            ) * dt
            self.odometry.y += (
                vel.linear_x * math.sin(self.odometry.theta)
                + vel.linear_y * math.cos(self.odometry.theta)
            ) * dt
            self.odometry.theta += vel.angular_z * dt
            time.sleep(dt)

    def set_velocity(self, linear_x: float, linear_y: float, angular_z: float) -> bool:
        """速度指令を送信する"""
        velocity = Velocity(linear_x, linear_y, angular_z)
        velocity = self._clamp_velocity(velocity)

        # メカナムホイールの各モーター速度を計算
        # FL, FR, RL, RR
        fl = velocity.linear_x - velocity.linear_y - velocity.angular_z
        fr = velocity.linear_x + velocity.linear_y + velocity.angular_z
        rl = velocity.linear_x + velocity.linear_y - velocity.angular_z
        rr = velocity.linear_x - velocity.linear_y + velocity.angular_z

        command = f"VEL {fl:.3f} {fr:.3f} {rl:.3f} {rr:.3f}"
        response = self._send_command(command)

        if response and response.startswith("OK"):
            self.current_velocity = velocity
            if linear_x == 0 and linear_y == 0 and angular_z == 0:
                self.state = BaseState.STOPPED
            elif angular_z != 0 and linear_x == 0 and linear_y == 0:
                self.state = BaseState.ROTATING
            else:
                self.state = BaseState.MOVING
            return True
        return False

    def move_forward(self, speed: float = 0.3) -> bool:
        """前進する"""
        return self.set_velocity(speed, 0.0, 0.0)

    def move_backward(self, speed: float = 0.3) -> bool:
        """後退する"""
        return self.set_velocity(-speed, 0.0, 0.0)

    def move_left(self, speed: float = 0.3) -> bool:
        """左に平行移動する"""
        return self.set_velocity(0.0, speed, 0.0)

    def move_right(self, speed: float = 0.3) -> bool:
        """右に平行移動する"""
        return self.set_velocity(0.0, -speed, 0.0)

    def rotate(self, angular_speed: float) -> bool:
        """その場で回転する (正=左回転, 負=右回転)"""
        return self.set_velocity(0.0, 0.0, angular_speed)

    def stop(self) -> bool:
        """停止する"""
        result = self.set_velocity(0.0, 0.0, 0.0)
        self.state = BaseState.STOPPED
        return result

    def move_to_point(self, target_x: float, target_y: float,
                      target_theta: Optional[float] = None) -> bool:
        """
        指定座標に移動する（シンプルなP制御）

        Args:
            target_x, target_y: 目標座標 (m)
            target_theta: 目標角度 (rad)。Noneの場合は目標方向を向く
        """
        logger.info(f"Moving to ({target_x:.2f}, {target_y:.2f})")
        tolerance = 0.1  # 10cm
        angle_tolerance = 0.1  # ~5.7度

        max_iterations = 1000
        for _ in range(max_iterations):
            dx = target_x - self.odometry.x
            dy = target_y - self.odometry.y
            distance = math.sqrt(dx ** 2 + dy ** 2)

            if distance < tolerance:
                break

            # 目標方向への角度
            target_angle = math.atan2(dy, dx)
            angle_error = target_angle - self.odometry.theta
            # -πからπに正規化
            angle_error = math.atan2(math.sin(angle_error), math.cos(angle_error))

            # まず回転、次に直進
            if abs(angle_error) > angle_tolerance:
                angular = self.config.pid_kp * angle_error
                self.set_velocity(0.0, 0.0, angular)
            else:
                speed = min(self.config.max_linear_speed, distance * self.config.pid_kp)
                self.set_velocity(speed, 0.0, 0.0)

            time.sleep(0.05)

        self.stop()

        # 最終的な向きを調整
        if target_theta is not None:
            for _ in range(200):
                angle_error = target_theta - self.odometry.theta
                angle_error = math.atan2(math.sin(angle_error), math.cos(angle_error))
                if abs(angle_error) < angle_tolerance:
                    break
                angular = self.config.pid_kp * angle_error
                self.set_velocity(0.0, 0.0, angular)
                time.sleep(0.05)
            self.stop()

        final_dist = math.sqrt(
            (target_x - self.odometry.x) ** 2
            + (target_y - self.odometry.y) ** 2
        )
        success = final_dist < tolerance * 2
        logger.info(f"Move complete: final_distance={final_dist:.3f}m, success={success}")
        return success

    def get_status(self) -> dict:
        """現在の状態を返す"""
        return {
            "state": self.state.value,
            "velocity": {
                "linear_x": self.current_velocity.linear_x,
                "linear_y": self.current_velocity.linear_y,
                "angular_z": self.current_velocity.angular_z,
            },
            "odometry": {
                "x": self.odometry.x,
                "y": self.odometry.y,
                "theta": self.odometry.theta,
            },
            "simulation_mode": self._simulation_mode,
        }
