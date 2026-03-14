"""
センサーモジュール

LiDAR、深度カメラ、超音波センサーなどのセンサーデータを管理する。
障害物検出と物体認識の基盤を提供する。
"""

import math
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from loguru import logger

try:
    import numpy as np
except ImportError:
    np = None
    logger.warning("numpy not installed")


@dataclass
class LidarScan:
    """LiDARスキャンデータ"""
    angles: list = field(default_factory=list)      # 角度 (degrees)
    distances: list = field(default_factory=list)    # 距離 (meters)
    timestamp: float = 0.0


@dataclass
class Obstacle:
    """検出された障害物"""
    x: float           # メートル
    y: float           # メートル
    distance: float    # メートル
    angle: float       # 度
    size: float = 0.1  # 推定サイズ (メートル)


class SensorManager:
    """センサーデータの統合管理"""

    def __init__(self):
        self._latest_lidar: Optional[LidarScan] = None
        self._obstacles: List[Obstacle] = []
        self._lock = threading.Lock()
        self._simulation_mode = True
        self._running = False
        logger.info("SensorManager initialized")

    def start(self):
        """センサーデータの取得を開始する"""
        self._running = True
        self._sim_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self._sim_thread.start()
        logger.info("Sensor data acquisition started")

    def stop(self):
        """センサーデータの取得を停止する"""
        self._running = False

    def _simulation_loop(self):
        """シミュレーション用のセンサーデータ生成"""
        import random
        while self._running:
            scan = LidarScan(timestamp=time.time())
            for angle in range(0, 360, 1):
                scan.angles.append(angle)
                # 部屋の壁をシミュレート (4m x 5m)
                rad = math.radians(angle)
                wall_dist = min(
                    abs(2.0 / math.cos(rad)) if abs(math.cos(rad)) > 0.01 else 99,
                    abs(2.5 / math.sin(rad)) if abs(math.sin(rad)) > 0.01 else 99,
                )
                wall_dist = min(wall_dist, 12.0)
                noise = random.gauss(0, 0.02)
                scan.distances.append(max(0.1, wall_dist + noise))

            with self._lock:
                self._latest_lidar = scan
                self._update_obstacles(scan)

            time.sleep(0.1)

    def _update_obstacles(self, scan: LidarScan):
        """LiDARデータから障害物を更新する"""
        obstacles = []
        threshold = 1.5  # 1.5m以内を障害物とみなす

        for angle, dist in zip(scan.angles, scan.distances):
            if dist < threshold:
                rad = math.radians(angle)
                obstacles.append(Obstacle(
                    x=dist * math.cos(rad),
                    y=dist * math.sin(rad),
                    distance=dist,
                    angle=angle,
                ))
        self._obstacles = obstacles

    def get_latest_scan(self) -> Optional[LidarScan]:
        """最新のLiDARスキャンを返す"""
        with self._lock:
            return self._latest_lidar

    def get_obstacles(self) -> List[Obstacle]:
        """検出された障害物リストを返す"""
        with self._lock:
            return list(self._obstacles)

    def check_path_clear(self, angle: float, distance: float,
                         corridor_width: float = 0.5) -> bool:
        """
        指定方向の経路が空いているか確認する

        Args:
            angle: 方向 (度)
            distance: チェック距離 (m)
            corridor_width: 通路幅 (m)
        """
        obstacles = self.get_obstacles()
        for obs in obstacles:
            angle_diff = abs(obs.angle - angle)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            if angle_diff < 30 and obs.distance < distance:
                # 通路幅内にあるか確認
                lateral_dist = obs.distance * math.sin(math.radians(angle_diff))
                if lateral_dist < corridor_width / 2:
                    return False
        return True

    def get_nearest_obstacle(self) -> Optional[Obstacle]:
        """最も近い障害物を返す"""
        obstacles = self.get_obstacles()
        if not obstacles:
            return None
        return min(obstacles, key=lambda o: o.distance)

    def get_status(self) -> dict:
        """センサーの状態を返す"""
        scan = self.get_latest_scan()
        obstacles = self.get_obstacles()
        nearest = self.get_nearest_obstacle()
        return {
            "lidar_active": scan is not None,
            "scan_points": len(scan.angles) if scan else 0,
            "obstacle_count": len(obstacles),
            "nearest_obstacle_distance": nearest.distance if nearest else None,
            "simulation_mode": self._simulation_mode,
        }
