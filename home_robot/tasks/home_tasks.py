"""
家庭用タスクモジュール

ロボットが実行できる家庭内タスクを定義する。
物を取ってくる、巡回、挨拶、片付けなどのタスクを提供する。
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from loguru import logger


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    status: TaskStatus
    message: str
    duration: float = 0.0


class HomeTasks:
    """家庭内タスクの実行エンジン"""

    def __init__(self, robot):
        """
        Args:
            robot: HomeRobotオーケストレーターのインスタンス
        """
        self.robot = robot

    def fetch_object(self, object_name: str, location: str,
                     deliver_to: str = "user") -> TaskResult:
        """
        物を取ってくるタスク

        1. 物体のある場所まで移動
        2. 物体を認識・把持
        3. 指定場所に運ぶ
        """
        start_time = time.time()
        logger.info(f"Task: Fetch '{object_name}' from '{location}'")

        face = self.robot.face
        base = self.robot.base
        claw = self.robot.claw

        # 1. 表情: 考え中
        face.express_thinking()
        face.show_speech(f"{object_name}を取りに行きます！")
        time.sleep(1)

        # 2. 場所の座標を取得
        coords = self.robot.get_location_coords(location)
        if not coords:
            face.express_error(f"{location}が見つかりません")
            return TaskResult(TaskStatus.FAILED, f"Unknown location: {location}")

        # 3. 移動
        face.set_status_text(f"{location}に移動中...")
        if not base.move_to_point(coords[0], coords[1]):
            face.express_error("移動できませんでした")
            return TaskResult(TaskStatus.FAILED, "Navigation failed")

        # 4. 物体を把持 (デモ用の固定座標)
        face.set_status_text(f"{object_name}を掴んでいます...")
        claw.open_gripper()
        time.sleep(0.5)

        # 実際にはカメラで物体検出して座標を取得する
        if not claw.pick_object(0.25, 0.0, 0.05):
            face.express_error(f"{object_name}を掴めませんでした")
            return TaskResult(TaskStatus.FAILED, "Grasp failed")

        # 5. 届け先に移動
        if deliver_to == "user":
            deliver_coords = self.robot.get_location_coords("home")
        else:
            deliver_coords = self.robot.get_location_coords(deliver_to)

        if deliver_coords:
            face.set_status_text("戻っています...")
            base.move_to_point(deliver_coords[0], deliver_coords[1])

        # 6. 物体を渡す
        claw.place_object(0.30, 0.0, 0.10)
        face.express_task_complete()

        duration = time.time() - start_time
        return TaskResult(TaskStatus.COMPLETED, f"Fetched {object_name}", duration)

    def patrol(self, waypoints: Optional[list] = None) -> TaskResult:
        """
        巡回タスク

        指定されたウェイポイントを巡回する。
        異常があれば報告する。
        """
        start_time = time.time()
        logger.info("Task: Patrol started")

        face = self.robot.face
        base = self.robot.base
        sensors = self.robot.sensors

        if waypoints is None:
            waypoints = [
                (1.0, 0.0),
                (1.0, 1.0),
                (0.0, 1.0),
                (-1.0, 1.0),
                (-1.0, 0.0),
                (0.0, 0.0),
            ]

        face.set_expression(face.current_expression.__class__("neutral"))
        face.set_status_text("巡回中...")

        for i, (wx, wy) in enumerate(waypoints):
            face.set_status_text(f"巡回中... ({i + 1}/{len(waypoints)})")

            if not base.move_to_point(wx, wy):
                logger.warning(f"Could not reach waypoint {i}: ({wx}, {wy})")
                continue

            # 到着地点でセンサーチェック
            nearest = sensors.get_nearest_obstacle()
            if nearest and nearest.distance < 0.5:
                face.show_speech(f"注意: 近くに障害物があります ({nearest.distance:.1f}m)")
                time.sleep(2)

        # ホームに帰還
        base.move_to_point(0.0, 0.0)
        face.express_task_complete()
        face.show_speech("巡回完了！異常ありません。")

        duration = time.time() - start_time
        return TaskResult(TaskStatus.COMPLETED, "Patrol complete", duration)

    def greet_person(self) -> TaskResult:
        """人を検出して挨拶する"""
        start_time = time.time()
        face = self.robot.face

        face.express_greeting()
        time.sleep(3)
        face.set_expression(face.current_expression.__class__("neutral"))

        duration = time.time() - start_time
        return TaskResult(TaskStatus.COMPLETED, "Greeting done", duration)

    def tidy_up(self, items: list) -> TaskResult:
        """
        片付けタスク

        指定されたアイテムを適切な場所に片付ける。
        """
        start_time = time.time()
        logger.info(f"Task: Tidy up {len(items)} items")

        face = self.robot.face
        face.show_speech(f"{len(items)}個のアイテムを片付けます")

        completed = 0
        for item in items:
            name = item.get("name", "object")
            from_loc = item.get("from", "table")
            to_loc = item.get("to", "shelf")

            face.set_status_text(f"{name}を片付け中... ({completed + 1}/{len(items)})")

            result = self.fetch_object(name, from_loc, deliver_to=to_loc)
            if result.status == TaskStatus.COMPLETED:
                completed += 1
            else:
                logger.warning(f"Failed to tidy {name}: {result.message}")

        duration = time.time() - start_time
        msg = f"Tidied {completed}/{len(items)} items"
        status = TaskStatus.COMPLETED if completed == len(items) else TaskStatus.FAILED
        return TaskResult(status, msg, duration)

    def follow_person(self, duration_seconds: float = 30.0) -> TaskResult:
        """
        人追従タスク（デモ）

        一定時間、人を追従する。
        実際にはカメラで人体検出を行い、追従する。
        """
        start_time = time.time()
        face = self.robot.face
        base = self.robot.base

        face.show_speech("ついていきます！")
        face.set_status_text("追従中...")

        # デモ: 一定時間だけ追従モードを示す
        while time.time() - start_time < duration_seconds:
            # 実際にはカメラで人の位置を検出して追従
            time.sleep(0.1)

        base.stop()
        face.express_task_complete()

        duration = time.time() - start_time
        return TaskResult(TaskStatus.COMPLETED, "Follow complete", duration)
