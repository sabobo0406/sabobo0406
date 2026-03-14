"""
Open Claw ロボットグリッパー制御モジュール

Open Clawのサーボモーターを制御し、物体の把持・解放を行う。
5軸アームの各ジョイント制御とグリッパーの開閉制御を提供する。
"""

import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from loguru import logger

try:
    import serial
except ImportError:
    serial = None
    logger.warning("pyserial not installed - running in simulation mode")


class ClawState(Enum):
    OPEN = "open"
    CLOSED = "closed"
    GRIPPING = "gripping"
    MOVING = "moving"
    ERROR = "error"
    IDLE = "idle"


@dataclass
class JointPosition:
    """各ジョイントの角度を保持する"""
    base_rotation: float = 0.0    # ベース回転
    shoulder: float = 45.0        # 肩
    elbow: float = 45.0           # 肘
    wrist_rotation: float = 0.0   # 手首回転
    gripper: float = 90.0         # グリッパー開閉 (0=閉, 180=開)


@dataclass
class GripperConfig:
    serial_port: str = "/dev/ttyUSB0"
    baud_rate: int = 115200
    min_aperture: int = 0
    max_aperture: int = 100
    min_angle: int = 0
    max_angle: int = 180
    max_grip_force: float = 10.0
    arm_joints: int = 5
    joint_limits: list = field(default_factory=lambda: [
        [-90, 90], [0, 135], [0, 135], [-90, 90], [0, 180]
    ])


class OpenClawController:
    """Open Claw グリッパーの制御クラス"""

    def __init__(self, config: Optional[GripperConfig] = None):
        self.config = config or GripperConfig()
        self.state = ClawState.IDLE
        self.current_position = JointPosition()
        self._serial: Optional[serial.Serial] = None
        self._lock = threading.Lock()
        self._simulation_mode = serial is None
        logger.info(f"OpenClawController initialized (simulation={self._simulation_mode})")

    def connect(self) -> bool:
        """シリアル接続を確立する"""
        if self._simulation_mode:
            logger.info("[SIM] Open Claw connected (simulation)")
            self.state = ClawState.IDLE
            return True

        try:
            self._serial = serial.Serial(
                port=self.config.serial_port,
                baudrate=self.config.baud_rate,
                timeout=1.0,
            )
            time.sleep(2)  # Arduino/サーボ初期化待ち
            self.state = ClawState.IDLE
            logger.info(f"Open Claw connected on {self.config.serial_port}")
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to connect Open Claw: {e}")
            self.state = ClawState.ERROR
            return False

    def disconnect(self):
        """接続を切断する"""
        if self._serial and self._serial.is_open:
            self._serial.close()
        self.state = ClawState.IDLE
        logger.info("Open Claw disconnected")

    def _send_command(self, command: str) -> Optional[str]:
        """シリアルコマンドを送信する"""
        with self._lock:
            if self._simulation_mode:
                logger.debug(f"[SIM] Command: {command}")
                return "OK"

            if not self._serial or not self._serial.is_open:
                logger.error("Serial port not open")
                return None

            self._serial.write(f"{command}\n".encode())
            response = self._serial.readline().decode().strip()
            return response

    def _validate_joint_angle(self, joint_index: int, angle: float) -> float:
        """ジョイント角度を制限範囲内に収める"""
        limits = self.config.joint_limits[joint_index]
        clamped = max(limits[0], min(limits[1], angle))
        if clamped != angle:
            logger.warning(
                f"Joint {joint_index} angle {angle} clamped to {clamped} "
                f"(limits: {limits})"
            )
        return clamped

    def move_joint(self, joint_index: int, angle: float, speed: int = 50) -> bool:
        """
        個別ジョイントを移動する

        Args:
            joint_index: ジョイント番号 (0-4)
            angle: 目標角度
            speed: 移動速度 (1-100)
        """
        if joint_index < 0 or joint_index >= self.config.arm_joints:
            logger.error(f"Invalid joint index: {joint_index}")
            return False

        angle = self._validate_joint_angle(joint_index, angle)
        speed = max(1, min(100, speed))

        self.state = ClawState.MOVING
        command = f"J{joint_index} {angle:.1f} {speed}"
        response = self._send_command(command)

        if response and response.startswith("OK"):
            # 現在位置を更新
            joint_names = ["base_rotation", "shoulder", "elbow",
                           "wrist_rotation", "gripper"]
            setattr(self.current_position, joint_names[joint_index], angle)
            self.state = ClawState.IDLE
            logger.info(f"Joint {joint_index} moved to {angle}°")
            return True

        self.state = ClawState.ERROR
        return False

    def move_to_position(self, position: JointPosition, speed: int = 50) -> bool:
        """全ジョイントを指定位置に移動する"""
        angles = [
            position.base_rotation,
            position.shoulder,
            position.elbow,
            position.wrist_rotation,
            position.gripper,
        ]

        self.state = ClawState.MOVING
        for i, angle in enumerate(angles):
            validated = self._validate_joint_angle(i, angle)
            angles[i] = validated

        command = "MA " + " ".join(f"{a:.1f}" for a in angles) + f" {speed}"
        response = self._send_command(command)

        if response and response.startswith("OK"):
            self.current_position = JointPosition(*angles)
            self.state = ClawState.IDLE
            logger.info(f"Arm moved to position: {angles}")
            return True

        self.state = ClawState.ERROR
        return False

    def open_gripper(self, aperture: float = 100.0) -> bool:
        """グリッパーを開く"""
        angle = (aperture / 100.0) * self.config.max_angle
        success = self.move_joint(4, angle)
        if success:
            self.state = ClawState.OPEN
        return success

    def close_gripper(self, force: Optional[float] = None) -> bool:
        """
        グリッパーを閉じて物体を把持する

        Args:
            force: 把持力 (N)。Noneの場合はデフォルト力を使用
        """
        if force and force > self.config.max_grip_force:
            logger.warning(
                f"Requested force {force}N exceeds max {self.config.max_grip_force}N"
            )
            force = self.config.max_grip_force

        force_param = force if force else self.config.max_grip_force * 0.5
        command = f"GRIP {force_param:.1f}"
        response = self._send_command(command)

        if response and response.startswith("OK"):
            self.state = ClawState.GRIPPING
            self.current_position.gripper = 0.0
            logger.info(f"Gripper closed with force {force_param}N")
            return True

        self.state = ClawState.ERROR
        return False

    def release(self) -> bool:
        """物体を解放する"""
        return self.open_gripper(100.0)

    def go_home(self) -> bool:
        """ホームポジションに移動する"""
        home = JointPosition(
            base_rotation=0.0,
            shoulder=45.0,
            elbow=45.0,
            wrist_rotation=0.0,
            gripper=90.0,
        )
        return self.move_to_position(home, speed=30)

    def pick_object(self, x: float, y: float, z: float) -> bool:
        """
        指定座標の物体をピックアップする

        逆運動学を使って目標座標からジョイント角度を計算し、
        物体を把持する一連の動作を実行する。

        Args:
            x, y, z: 物体の座標 (ロボットベース基準, メートル)
        """
        import math

        logger.info(f"Picking object at ({x:.3f}, {y:.3f}, {z:.3f})")

        # 簡易的な逆運動学 (2リンクアーム近似)
        L1 = 0.20  # 上腕長 (m)
        L2 = 0.18  # 前腕長 (m)

        # ベース回転角
        base_angle = math.degrees(math.atan2(y, x))

        # 水平距離と高さ
        r = math.sqrt(x ** 2 + y ** 2)
        h = z

        dist = math.sqrt(r ** 2 + h ** 2)
        if dist > L1 + L2:
            logger.error(f"Target out of reach: distance={dist:.3f}m")
            return False

        # 2リンク逆運動学
        cos_elbow = (dist ** 2 - L1 ** 2 - L2 ** 2) / (2 * L1 * L2)
        cos_elbow = max(-1.0, min(1.0, cos_elbow))
        elbow_angle = math.degrees(math.acos(cos_elbow))

        alpha = math.atan2(h, r)
        beta = math.acos((L1 ** 2 + dist ** 2 - L2 ** 2) / (2 * L1 * dist))
        shoulder_angle = math.degrees(alpha + beta)

        # 1. アプローチ位置へ移動（物体の上）
        approach = JointPosition(
            base_rotation=base_angle,
            shoulder=shoulder_angle + 15,  # 少し上
            elbow=elbow_angle,
            wrist_rotation=0.0,
            gripper=180.0,  # グリッパー全開
        )
        if not self.move_to_position(approach, speed=40):
            return False
        time.sleep(0.5)

        # 2. 下降して物体位置へ
        grasp_pos = JointPosition(
            base_rotation=base_angle,
            shoulder=shoulder_angle,
            elbow=elbow_angle,
            wrist_rotation=0.0,
            gripper=180.0,
        )
        if not self.move_to_position(grasp_pos, speed=20):
            return False
        time.sleep(0.3)

        # 3. グリッパーを閉じて把持
        if not self.close_gripper():
            return False
        time.sleep(0.5)

        # 4. 持ち上げ
        lift_pos = JointPosition(
            base_rotation=base_angle,
            shoulder=shoulder_angle + 30,
            elbow=elbow_angle - 10,
            wrist_rotation=0.0,
            gripper=0.0,
        )
        if not self.move_to_position(lift_pos, speed=30):
            return False

        logger.info("Object picked up successfully")
        return True

    def place_object(self, x: float, y: float, z: float) -> bool:
        """指定座標に物体を置く"""
        import math

        logger.info(f"Placing object at ({x:.3f}, {y:.3f}, {z:.3f})")

        L1 = 0.20
        L2 = 0.18

        base_angle = math.degrees(math.atan2(y, x))
        r = math.sqrt(x ** 2 + y ** 2)
        h = z
        dist = math.sqrt(r ** 2 + h ** 2)

        if dist > L1 + L2:
            logger.error(f"Target out of reach: distance={dist:.3f}m")
            return False

        cos_elbow = (dist ** 2 - L1 ** 2 - L2 ** 2) / (2 * L1 * L2)
        cos_elbow = max(-1.0, min(1.0, cos_elbow))
        elbow_angle = math.degrees(math.acos(cos_elbow))

        alpha = math.atan2(h, r)
        beta = math.acos((L1 ** 2 + dist ** 2 - L2 ** 2) / (2 * L1 * dist))
        shoulder_angle = math.degrees(alpha + beta)

        # 1. 配置位置へ移動
        place_pos = JointPosition(
            base_rotation=base_angle,
            shoulder=shoulder_angle,
            elbow=elbow_angle,
            wrist_rotation=0.0,
            gripper=0.0,
        )
        if not self.move_to_position(place_pos, speed=30):
            return False
        time.sleep(0.3)

        # 2. グリッパーを開いて解放
        if not self.release():
            return False
        time.sleep(0.3)

        # 3. 退避
        self.go_home()
        logger.info("Object placed successfully")
        return True

    def get_status(self) -> dict:
        """現在の状態を返す"""
        pos = self.current_position
        return {
            "state": self.state.value,
            "position": {
                "base_rotation": pos.base_rotation,
                "shoulder": pos.shoulder,
                "elbow": pos.elbow,
                "wrist_rotation": pos.wrist_rotation,
                "gripper": pos.gripper,
            },
            "simulation_mode": self._simulation_mode,
        }
