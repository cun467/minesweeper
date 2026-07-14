"""
扫雷游戏核心逻辑模块。

提供 Cell 和 Board 两个核心类，实现扫雷游戏的所有基本规则：
  - 首次点击安全（点击位置及其相邻格不会是雷）
  - 揭开地雷则游戏结束
  - 相邻雷数为 0 时自动 flood fill 展开
  - 插旗/取消插旗标记
  - 胜利判定

坐标原点为棋盘左上角 (0, 0)，x 轴向右增长，y 轴向下增长。

Examples:
    >>> board = Board(9, 9, 10)
    >>> board.reveal(4, 4)     # 首次点击，触发布雷
    >>> board.toggle_flag(3, 3)
    >>> board.check_win()
"""

import random
from typing import List, Set, Tuple, Union


class Cell:
    """扫雷游戏中的单个格子。

    Attributes:
        is_mine: 该格子是否为地雷。
        is_revealed: 该格子是否已被揭开。
        is_flagged: 该格子是否被标记（插旗）。
        adjacent_mines: 相邻 8 格中所含地雷的数量（0–8）。
    """

    __slots__ = ("is_mine", "is_revealed", "is_flagged", "adjacent_mines")

    def __init__(self) -> None:
        """初始化一个未揭开、未标记、非雷、相邻雷数为 0 的格子。"""
        self.is_mine: bool = False
        self.is_revealed: bool = False
        self.is_flagged: bool = False
        self.adjacent_mines: int = 0

    def __repr__(self) -> str:
        return (
            f"Cell(mine={self.is_mine}, revealed={self.is_revealed}, "
            f"flagged={self.is_flagged}, adjacent={self.adjacent_mines})"
        )


class Board:
    """扫雷游戏棋盘。

    负责管理整个网格状态，包括布雷、揭开、标记和胜负判定。

    Attributes:
        width: 棋盘宽度（列数）。
        height: 棋盘高度（行数）。
        mine_count: 地雷总数。
        grid: 二维列表，通过 ``grid[y][x]`` 访问坐标 (x, y) 处的 Cell 对象。
    """

    # 8 方向偏移量（类常量）
    _DIRECTIONS: List[Tuple[int, int]] = [
        (-1, -1), (0, -1), (1, -1),
        (-1,  0),          (1,  0),
        (-1,  1), (0,  1), (1,  1),
    ]

    def __init__(self, width: int, height: int, mine_count: int) -> None:
        """初始化棋盘。

        Args:
            width: 棋盘宽度（列数），必须大于 0。
            height: 棋盘高度（行数），必须大于 0。
            mine_count: 地雷总数，必须满足 0 < mine_count < width * height。

        Raises:
            ValueError: 当参数不合法时抛出。
        """
        if width <= 0 or height <= 0:
            raise ValueError("棋盘宽度和高度必须大于 0")
        if mine_count <= 0:
            raise ValueError("地雷数量必须大于 0")
        if mine_count >= width * height:
            raise ValueError("地雷数量不能大于或等于格子总数")

        self.width: int = width
        self.height: int = height
        self.mine_count: int = mine_count
        self.grid: List[List[Cell]] = [
            [Cell() for _ in range(width)] for _ in range(height)
        ]

        # ---- 内部状态 -------------------------------------------------------
        self._mines_placed: bool = False   # 是否已布雷（首次点击触发）
        self._game_over: bool = False      # 是否已踩雷结束
        self._revealed_count: int = 0      # 已揭开格子数（不含地雷）

    # ------------------------------------------------------------------
    # 公共方法
    # ------------------------------------------------------------------

    def reveal(self, x: int, y: int) -> Union[Set[Tuple[int, int]], str]:
        """揭开坐标 (x, y) 处的格子。

        首次点击时会自动布雷，并确保点击位置及其相邻格不会是雷。
        若揭开的格子相邻地雷数为 0，则自动进行 flood fill 展开。
        若揭开的是地雷，游戏立即结束并返回 ``"game_over"``。

        Args:
            x: 格子的 x 坐标（列），左上角为 0。
            y: 格子的 y 坐标（行），左上角为 0。

        Returns:
            若踩雷则返回字符串 ``"game_over"``；
            否则返回本次操作新揭开的坐标集合 ``{(x, y), ...}``。

        Raises:
            IndexError: 坐标超出棋盘范围时抛出。
            ValueError: 游戏已结束、格子已被揭开或处于标记状态时抛出。

        Example:
            >>> board = Board(5, 5, 3)
            >>> result = board.reveal(2, 2)
            >>> isinstance(result, set)
            True
        """
        self._validate_coord(x, y)

        if self._game_over:
            raise ValueError("游戏已结束，无法继续操作")

        cell = self.grid[y][x]

        if cell.is_revealed:
            raise ValueError(f"({x}, {y}) 已被揭开")

        if cell.is_flagged:
            raise ValueError(f"({x}, {y}) 已被标记，请先取消标记再揭开")

        # 首次点击 → 布雷（保证点击位置安全）
        if not self._mines_placed:
            self._place_mines(safe_x=x, safe_y=y)

        # 踩雷 → 游戏结束
        if cell.is_mine:
            cell.is_revealed = True
            self._game_over = True
            return "game_over"

        # 正常揭开（含 flood fill）
        revealed: Set[Tuple[int, int]] = set()
        self._reveal_recursive(x, y, revealed)
        return revealed

    def toggle_flag(self, x: int, y: int) -> bool:
        """切换坐标 (x, y) 处格子的标记（插旗/取消插旗）状态。

        已揭开的格子无法标记，已标记的格子再次调用会取消标记。

        Args:
            x: 格子的 x 坐标（列）。
            y: 格子的 y 坐标（行）。

        Returns:
            操作后该格子的标记状态，``True`` 表示已标记，``False`` 表示未标记。

        Raises:
            IndexError: 坐标超出棋盘范围时抛出。
            ValueError: 游戏已结束或格子已被揭开时抛出。
        """
        self._validate_coord(x, y)

        if self._game_over:
            raise ValueError("游戏已结束，无法继续操作")

        cell = self.grid[y][x]

        if cell.is_revealed:
            raise ValueError(f"({x}, {y}) 已被揭开，无法标记")

        cell.is_flagged = not cell.is_flagged
        return cell.is_flagged

    def check_win(self) -> bool:
        """判定是否已经胜利。

        胜利条件：所有非雷格子均已被揭开（即 ``已揭开数 == 总格子数 - 雷数``）。

        Returns:
            ``True`` 表示胜利，``False`` 表示尚未胜利。
        """
        if self._game_over:
            return False
        return self._revealed_count == (self.width * self.height - self.mine_count)

    @property
    def is_game_over(self) -> bool:
        """游戏是否已结束（踩雷）。"""
        return self._game_over

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _validate_coord(self, x: int, y: int) -> None:
        """校验坐标是否在棋盘范围内。

        Args:
            x: x 坐标（列）。
            y: y 坐标（行）。

        Raises:
            IndexError: 坐标越界时抛出。
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(
                f"坐标 ({x}, {y}) 超出棋盘范围 [{self.width}x{self.height}]"
            )

    def _neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        """返回 (x, y) 周围 8 方向中在棋盘范围内的邻居坐标。

        Args:
            x: 中心格子的 x 坐标。
            y: 中心格子的 y 坐标。

        Returns:
            有效邻居坐标列表（顺序固定）。
        """
        result: List[Tuple[int, int]] = []
        for dx, dy in self._DIRECTIONS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                result.append((nx, ny))
        return result

    def _place_mines(self, safe_x: int, safe_y: int) -> None:
        """首次点击时布雷。

        保证 ``safe_x, safe_y`` 及其相邻格不是地雷（首次点击安全规则）。
        布雷后更新所有非雷格子的 adjacent_mines 计数。

        Args:
            safe_x: 安全区域的中心 x 坐标。
            safe_y: 安全区域的中心 y 坐标。
        """
        # 构建安全区域（点击位置 + 周围 8 格中在棋盘内的部分）
        safe_cells: Set[Tuple[int, int]] = {(safe_x, safe_y)}
        for nx, ny in self._neighbors(safe_x, safe_y):
            safe_cells.add((nx, ny))

        # 收集所有可布雷的候选位置
        candidates: List[Tuple[int, int]] = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if (x, y) not in safe_cells
        ]

        if self.mine_count > len(candidates):
            raise RuntimeError(
                f"地雷数量 ({self.mine_count}) 超过可用位置 ({len(candidates)})，"
                f"无法保证首次点击安全"
            )

        # 随机选取雷位
        for mx, my in random.sample(candidates, self.mine_count):
            self.grid[my][mx].is_mine = True

        # 计算每个非雷格子的 adjacent_mines
        for y in range(self.height):
            for x in range(self.width):
                cell = self.grid[y][x]
                if cell.is_mine:
                    continue
                cell.adjacent_mines = sum(
                    1 for nx, ny in self._neighbors(x, y) if self.grid[ny][nx].is_mine
                )

        self._mines_placed = True

    def _reveal_recursive(
        self, x: int, y: int, revealed: Set[Tuple[int, int]]
    ) -> None:
        """递归揭开格子并 flood fill。

        若当前格子 adjacent_mines == 0，则自动递归揭开所有相邻格。

        Args:
            x: 当前格子的 x 坐标。
            y: 当前格子的 y 坐标。
            revealed: 累积本次操作新揭开坐标的集合。
        """
        cell = self.grid[y][x]

        # 终止条件：已揭开 / 已标记 / 是地雷
        if cell.is_revealed or cell.is_flagged or cell.is_mine:
            return

        cell.is_revealed = True
        self._revealed_count += 1
        revealed.add((x, y))

        # 相邻雷数为 0 → flood fill 展开
        if cell.adjacent_mines == 0:
            for nx, ny in self._neighbors(x, y):
                self._reveal_recursive(nx, ny, revealed)
