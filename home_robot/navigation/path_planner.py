"""
経路計画モジュール

A*アルゴリズムを使用した室内経路計画。
占有格子地図上で障害物を回避しながら目標地点への経路を生成する。
"""

import heapq
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class GridMap:
    """占有格子地図"""
    width: int = 100       # グリッド幅
    height: int = 100      # グリッド高さ
    resolution: float = 0.05  # メートル/ピクセル
    origin_x: float = -2.5    # 地図原点 (m)
    origin_y: float = -2.5
    data: list = field(default_factory=list)

    def __post_init__(self):
        if not self.data:
            self.data = [0] * (self.width * self.height)

    def world_to_grid(self, wx: float, wy: float) -> Tuple[int, int]:
        """ワールド座標をグリッド座標に変換"""
        gx = int((wx - self.origin_x) / self.resolution)
        gy = int((wy - self.origin_y) / self.resolution)
        return max(0, min(self.width - 1, gx)), max(0, min(self.height - 1, gy))

    def grid_to_world(self, gx: int, gy: int) -> Tuple[float, float]:
        """グリッド座標をワールド座標に変換"""
        wx = gx * self.resolution + self.origin_x
        wy = gy * self.resolution + self.origin_y
        return wx, wy

    def is_occupied(self, gx: int, gy: int) -> bool:
        """指定セルが占有されているか"""
        if gx < 0 or gx >= self.width or gy < 0 or gy >= self.height:
            return True
        return self.data[gy * self.width + gx] > 50

    def set_occupied(self, gx: int, gy: int, value: int = 100):
        """セルの占有状態を設定"""
        if 0 <= gx < self.width and 0 <= gy < self.height:
            self.data[gy * self.width + gx] = value

    def inflate_obstacles(self, radius_cells: int):
        """障害物を膨張させる（安全マージン）"""
        inflated = list(self.data)
        for y in range(self.height):
            for x in range(self.width):
                if self.data[y * self.width + x] > 50:
                    for dy in range(-radius_cells, radius_cells + 1):
                        for dx in range(-radius_cells, radius_cells + 1):
                            if dx * dx + dy * dy <= radius_cells * radius_cells:
                                nx, ny = x + dx, y + dy
                                if 0 <= nx < self.width and 0 <= ny < self.height:
                                    inflated[ny * self.width + nx] = max(
                                        inflated[ny * self.width + nx], 80
                                    )
        self.data = inflated


@dataclass
class PathPoint:
    """経路上の点"""
    x: float
    y: float


class AStarPlanner:
    """A*経路計画"""

    def __init__(self, grid_map: Optional[GridMap] = None):
        self.grid_map = grid_map or GridMap()

    def plan(self, start_x: float, start_y: float,
             goal_x: float, goal_y: float) -> Optional[List[PathPoint]]:
        """
        A*で経路を計画する

        Args:
            start_x, start_y: 開始座標 (m)
            goal_x, goal_y: 目標座標 (m)

        Returns:
            PathPointのリスト、経路が見つからなければNone
        """
        sx, sy = self.grid_map.world_to_grid(start_x, start_y)
        gx, gy = self.grid_map.world_to_grid(goal_x, goal_y)

        if self.grid_map.is_occupied(sx, sy):
            logger.error("Start position is occupied")
            return None
        if self.grid_map.is_occupied(gx, gy):
            logger.error("Goal position is occupied")
            return None

        # A* search
        open_set: List[Tuple[float, int, int]] = []
        heapq.heappush(open_set, (0.0, sx, sy))

        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], float] = {(sx, sy): 0.0}

        # 8方向移動
        directions = [
            (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
            (1, 1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (-1, -1, 1.414),
        ]

        while open_set:
            _, cx, cy = heapq.heappop(open_set)

            if cx == gx and cy == gy:
                return self._reconstruct_path(came_from, (gx, gy))

            for dx, dy, cost in directions:
                nx, ny = cx + dx, cy + dy
                if self.grid_map.is_occupied(nx, ny):
                    continue

                new_g = g_score[(cx, cy)] + cost
                if (nx, ny) not in g_score or new_g < g_score[(nx, ny)]:
                    g_score[(nx, ny)] = new_g
                    h = math.sqrt((nx - gx) ** 2 + (ny - gy) ** 2)
                    f = new_g + h
                    heapq.heappush(open_set, (f, nx, ny))
                    came_from[(nx, ny)] = (cx, cy)

        logger.warning("No path found")
        return None

    def _reconstruct_path(self, came_from: Dict, goal: Tuple[int, int]) -> List[PathPoint]:
        """経路を再構築する"""
        path_grid = [goal]
        current = goal
        while current in came_from:
            current = came_from[current]
            path_grid.append(current)
        path_grid.reverse()

        # グリッド座標をワールド座標に変換
        path = []
        for gx, gy in path_grid:
            wx, wy = self.grid_map.grid_to_world(gx, gy)
            path.append(PathPoint(x=wx, y=wy))

        # 経路を簡略化（直線区間をまとめる）
        simplified = self._simplify_path(path)
        logger.info(f"Path found: {len(path)} -> {len(simplified)} points")
        return simplified

    def _simplify_path(self, path: List[PathPoint],
                       tolerance: float = 0.1) -> List[PathPoint]:
        """Douglas-Peuckerアルゴリズムで経路を簡略化する"""
        if len(path) <= 2:
            return path

        # 最大距離の点を見つける
        max_dist = 0.0
        max_idx = 0
        start = path[0]
        end = path[-1]

        for i in range(1, len(path) - 1):
            dist = self._point_line_distance(path[i], start, end)
            if dist > max_dist:
                max_dist = dist
                max_idx = i

        if max_dist > tolerance:
            left = self._simplify_path(path[:max_idx + 1], tolerance)
            right = self._simplify_path(path[max_idx:], tolerance)
            return left[:-1] + right
        else:
            return [start, end]

    @staticmethod
    def _point_line_distance(point: PathPoint,
                             line_start: PathPoint,
                             line_end: PathPoint) -> float:
        """点から線分への距離を計算する"""
        dx = line_end.x - line_start.x
        dy = line_end.y - line_start.y
        length_sq = dx * dx + dy * dy

        if length_sq == 0:
            return math.sqrt(
                (point.x - line_start.x) ** 2 + (point.y - line_start.y) ** 2
            )

        t = max(0, min(1, (
            (point.x - line_start.x) * dx + (point.y - line_start.y) * dy
        ) / length_sq))

        proj_x = line_start.x + t * dx
        proj_y = line_start.y + t * dy

        return math.sqrt((point.x - proj_x) ** 2 + (point.y - proj_y) ** 2)

    def update_map_from_lidar(self, robot_x: float, robot_y: float,
                              robot_theta: float, angles: list,
                              distances: list):
        """LiDARデータで地図を更新する"""
        for angle, dist in zip(angles, distances):
            if dist < 0.1 or dist > 10.0:
                continue
            world_angle = math.radians(angle) + robot_theta
            ox = robot_x + dist * math.cos(world_angle)
            oy = robot_y + dist * math.sin(world_angle)
            gx, gy = self.grid_map.world_to_grid(ox, oy)
            self.grid_map.set_occupied(gx, gy, 100)
