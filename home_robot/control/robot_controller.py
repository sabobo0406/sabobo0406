"""
HomeBot メインオーケストレーター

全モジュール（Open Claw、移動ベース、MegPadディスプレイ、センサー、
ナビゲーション）を統合し、家庭用ロボット全体を制御する。
"""

import signal
import sys
import time
from typing import Dict, Optional, Tuple

import yaml
from loguru import logger

from home_robot.hardware.open_claw import OpenClawController, GripperConfig
from home_robot.hardware.mobile_base import MobileBaseController, BaseConfig
from home_robot.display.face_ui import MegPadFaceUI, DisplayConfig, Expression
from home_robot.navigation.sensors import SensorManager
from home_robot.navigation.path_planner import AStarPlanner
from home_robot.tasks.home_tasks import HomeTasks


# 家の中の場所定義（カスタマイズ可能）
DEFAULT_LOCATIONS: Dict[str, Tuple[float, float]] = {
    "home": (0.0, 0.0),
    "kitchen": (2.0, 0.0),
    "living_room": (0.0, 2.0),
    "bedroom": (-2.0, 1.0),
    "entrance": (0.0, -2.0),
    "table": (1.0, 1.0),
    "shelf": (-1.0, 0.5),
    "fridge": (2.0, 0.5),
    "sofa": (0.5, 2.0),
}


class HomeRobot:
    """
    家庭用ロボット統合制御クラス

    KTC MegPad 27インチスマートモニター + Open Clawグリッパー +
    メカナムホイール移動ベースを組み合わせた家庭用ロボット。
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.locations = dict(DEFAULT_LOCATIONS)

        # --- ハードウェア初期化 ---
        claw_cfg = self._build_claw_config()
        self.claw = OpenClawController(claw_cfg)

        base_cfg = self._build_base_config()
        self.base = MobileBaseController(base_cfg)

        display_cfg = DisplayConfig()
        self.face = MegPadFaceUI(display_cfg)

        # --- ナビゲーション ---
        self.sensors = SensorManager()
        self.planner = AStarPlanner()

        # --- タスクエンジン ---
        self.tasks = HomeTasks(self)

        self._running = False
        logger.info("HomeRobot initialized")

    def _load_config(self, path: Optional[str]) -> dict:
        """設定ファイルを読み込む"""
        if path:
            try:
                with open(path) as f:
                    return yaml.safe_load(f)
            except FileNotFoundError:
                logger.warning(f"Config not found: {path}, using defaults")
        return {}

    def _build_claw_config(self) -> GripperConfig:
        """設定からGripperConfigを構築する"""
        oc = self.config.get("open_claw", {})
        return GripperConfig(
            serial_port=oc.get("serial_port", "/dev/ttyUSB0"),
            baud_rate=oc.get("baud_rate", 115200),
            max_grip_force=oc.get("max_grip_force", 10.0),
        )

    def _build_base_config(self) -> BaseConfig:
        """設定からBaseConfigを構築する"""
        mb = self.config.get("mobile_base", {})
        return BaseConfig(
            serial_port=mb.get("serial_port", "/dev/ttyUSB1"),
            baud_rate=mb.get("baud_rate", 115200),
            max_linear_speed=mb.get("max_linear_speed", 0.5),
            max_angular_speed=mb.get("max_angular_speed", 1.0),
        )

    def startup(self) -> bool:
        """全システムを起動する"""
        logger.info("=" * 50)
        logger.info("  HomeBot Starting Up...")
        logger.info("=" * 50)

        # 1. ディスプレイ起動
        self.face.start()
        self.face.set_expression(Expression.THINKING)
        self.face.set_status_text("起動中...")

        # 2. Open Claw接続
        if not self.claw.connect():
            logger.error("Failed to connect Open Claw")
            self.face.express_error("アームの接続に失敗しました")
            return False
        self.claw.go_home()

        # 3. 移動ベース接続
        if not self.base.connect():
            logger.error("Failed to connect mobile base")
            self.face.express_error("移動ベースの接続に失敗しました")
            return False

        # 4. センサー起動
        self.sensors.start()

        # 5. 起動完了
        self._running = True
        self.face.set_expression(Expression.HAPPY)
        self.face.show_speech("こんにちは！HomeBotです。準備完了しました！", duration_ms=5000)
        self.face.set_status_text("Ready")

        logger.info("HomeBot startup complete")
        return True

    def shutdown(self):
        """全システムを安全にシャットダウンする"""
        logger.info("HomeBot shutting down...")
        self._running = False

        self.face.show_speech("おやすみなさい...", duration_ms=3000)
        self.face.set_expression(Expression.SLEEPING)
        time.sleep(1)

        self.claw.go_home()
        self.claw.disconnect()
        self.base.stop()
        self.base.disconnect()
        self.sensors.stop()
        self.face.stop()

        logger.info("HomeBot shutdown complete")

    def get_location_coords(self, name: str) -> Optional[Tuple[float, float]]:
        """場所名から座標を取得する"""
        return self.locations.get(name.lower())

    def add_location(self, name: str, x: float, y: float):
        """新しい場所を登録する"""
        self.locations[name.lower()] = (x, y)
        logger.info(f"Location added: {name} -> ({x}, {y})")

    def navigate_to(self, location_name: str) -> bool:
        """名前で指定した場所に移動する"""
        coords = self.get_location_coords(location_name)
        if not coords:
            logger.error(f"Unknown location: {location_name}")
            self.face.express_error(f"{location_name}が見つかりません")
            return False

        self.face.set_status_text(f"{location_name}に移動中...")
        self.face.set_expression(Expression.NEUTRAL)

        # 経路計画
        path = self.planner.plan(
            self.base.odometry.x, self.base.odometry.y,
            coords[0], coords[1],
        )

        if path:
            # ウェイポイントに沿って移動
            for point in path:
                if not self._running:
                    return False
                self.base.move_to_point(point.x, point.y)
        else:
            # 直接移動
            self.base.move_to_point(coords[0], coords[1])

        self.face.show_speech(f"{location_name}に着きました！", duration_ms=3000)
        return True

    def fetch(self, object_name: str, location: str) -> bool:
        """物を取ってくる（簡易インターフェース）"""
        result = self.tasks.fetch_object(object_name, location)
        return result.status.value == "completed"

    def patrol(self) -> bool:
        """巡回する"""
        result = self.tasks.patrol()
        return result.status.value == "completed"

    def get_full_status(self) -> dict:
        """全システムの状態を返す"""
        return {
            "running": self._running,
            "claw": self.claw.get_status(),
            "base": self.base.get_status(),
            "face": self.face.get_status(),
            "sensors": self.sensors.get_status(),
            "locations": self.locations,
        }

    def run_interactive(self):
        """対話モードで実行する"""
        if not self.startup():
            return

        def signal_handler(sig, frame):
            self.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        print("\n=== HomeBot Interactive Mode ===")
        print("Commands:")
        print("  go <location>        - Move to location")
        print("  fetch <object> <loc> - Fetch object from location")
        print("  patrol               - Start patrol")
        print("  greet                - Greet")
        print("  status               - Show status")
        print("  locations            - List locations")
        print("  quit                 - Shutdown")
        print()

        while self._running:
            try:
                cmd = input("HomeBot> ").strip().lower()
            except EOFError:
                break

            if not cmd:
                continue

            parts = cmd.split()
            action = parts[0]

            if action == "quit" or action == "exit":
                break
            elif action == "go" and len(parts) >= 2:
                self.navigate_to(parts[1])
            elif action == "fetch" and len(parts) >= 3:
                self.fetch(parts[1], parts[2])
            elif action == "patrol":
                self.patrol()
            elif action == "greet":
                self.tasks.greet_person()
            elif action == "status":
                import json
                print(json.dumps(self.get_full_status(), indent=2, default=str))
            elif action == "locations":
                for name, (x, y) in self.locations.items():
                    print(f"  {name}: ({x:.1f}, {y:.1f})")
            else:
                print(f"Unknown command: {cmd}")

        self.shutdown()


def main():
    """メインエントリポイント"""
    import argparse
    parser = argparse.ArgumentParser(description="HomeBot - 家庭用ロボット")
    parser.add_argument("--config", type=str, default=None, help="Config file path")
    args = parser.parse_args()

    robot = HomeRobot(config_path=args.config)
    robot.run_interactive()


if __name__ == "__main__":
    main()
