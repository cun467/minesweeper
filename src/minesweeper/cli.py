"""
扫雷游戏命令行界面。

用法::

    python -m minesweeper.cli          # 从 src/ 目录运行
    python cli.py                      # 直接从文件运行

进入游戏后:
    - 选择难度（1 初级 / 2 中级 / 3 高级 / 4 自定义）
    - ``r x y``  揭开坐标 (x, y) 处的格子
    - ``f x y``  标记/取消标记坐标 (x, y)
    - ``q``      退出游戏

坐标原点为棋盘左上角 (0, 0)，x 向右增长，y 向下增长。
"""

from __future__ import annotations

import os
import sys
import time

# 确保 src/ 在 sys.path 中，使 ``from minesweeper.core import Board`` 能正常工作
_here = os.path.dirname(os.path.abspath(__file__))
_src = os.path.dirname(_here)  # src/
if _src not in sys.path:
    sys.path.insert(0, _src)

from minesweeper.core import Board  # noqa: E402


# ---------------------------------------------------------------------------
# ANSI 颜色常量（Windows 10+ / PyCharm 终端均支持）
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"

# 数字颜色（1–8）
_NUMBER_COLORS: dict[int, str] = {
    1: "\033[34m",   # 蓝
    2: "\033[32m",   # 绿
    3: "\033[31m",   # 红
    4: "\033[35m",   # 紫
    5: "\033[33m",   # 黄
    6: "\033[36m",   # 青
    7: "\033[90m",   # 灰
    8: "\033[37m",   # 白
}

_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_GRAY = "\033[90m"

# 格子显示符号
_UNOPENED = "█"
_FLAGGED = "⚑"
_MINE = "*"
_EMPTY = " "


# ---------------------------------------------------------------------------
# 难度预设
# ---------------------------------------------------------------------------

PRESETS = {
    "1": ("初级", 9, 9, 10),
    "2": ("中级", 16, 16, 40),
    "3": ("高级", 30, 16, 99),
}


# ===================================================================
# 主游戏类
# ===================================================================

class MinesweeperCLI:
    """扫雷命令行界面控制器。"""

    def __init__(self) -> None:
        self.board: Board | None = None
        self._start_time: float = 0.0

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------

    def run(self) -> None:
        """启动游戏主循环。"""
        self._print_header()
        self._select_difficulty()
        self._game_loop()

    # ------------------------------------------------------------------
    # 难度选择
    # ------------------------------------------------------------------

    def _select_difficulty(self) -> None:
        """交互式选择难度。"""
        print(f"{_BOLD}请选择难度:{_RESET}\n")
        print("  1. 初级  (9×9,  10 雷)")
        print("  2. 中级  (16×16, 40 雷)")
        print("  3. 高级  (30×16, 99 雷)")
        print("  4. 自定义\n")

        while True:
            choice = input(">>> ").strip()
            if choice in PRESETS:
                name, w, h, m = PRESETS[choice]
                self.board = Board(w, h, m)
                print(f"\n{_GREEN}已选择: {name}{_RESET}\n")
                return
            elif choice == "4":
                self._custom_difficulty()
                return
            else:
                print(f"{_RED}请输入 1–4{_RESET}")

    def _custom_difficulty(self) -> None:
        """自定义棋盘尺寸和雷数。"""
        print(f"\n{_BOLD}自定义难度{_RESET}")
        while True:
            try:
                w = int(input("  宽度 (5–50): ").strip())
                h = int(input("  高度 (5–30): ").strip())
                m = int(input("  雷数: ").strip())
                if not (5 <= w <= 50):
                    print(f"{_RED}宽度需在 5–50 之间{_RESET}")
                    continue
                if not (5 <= h <= 30):
                    print(f"{_RED}高度需在 5–30 之间{_RESET}")
                    continue
                self.board = Board(w, h, m)
                print(f"\n{_GREEN}已创建 {w}×{h}, {m} 雷{_RESET}\n")
                return
            except ValueError as e:
                print(f"{_RED}{e}{_RESET}")

    # ------------------------------------------------------------------
    # 游戏主循环
    # ------------------------------------------------------------------

    def _game_loop(self) -> None:
        """主交互循环：渲染→读取命令→执行→判定胜负。"""
        assert self.board is not None
        self._start_time = time.time()

        while True:
            self._render()

            if self.board.check_win():
                elapsed = int(time.time() - self._start_time)
                self._render(reveal_all=True)
                print(f"\n{_GREEN}{_BOLD}🎉 你赢了！ 用时 {elapsed} 秒{_RESET}\n")
                break

            if self.board.is_game_over:
                self._render(reveal_all=True)
                print(f"\n{_RED}{_BOLD}💣 踩雷了！游戏结束{_RESET}\n")
                break

            cmd = input(f"\n{_BOLD}> {_RESET}").strip().lower()
            if not cmd:
                continue

            if cmd == "q":
                print(f"{_YELLOW}已退出{_RESET}")
                break

            parts = cmd.split()
            if len(parts) != 3:
                self._print_help()
                continue

            action, *coords = parts
            try:
                x, y = int(coords[0]), int(coords[1])
            except ValueError:
                self._print_help()
                continue

            if action == "r":
                self._do_reveal(x, y)
            elif action == "f":
                self._do_flag(x, y)
            else:
                self._print_help()

    # ------------------------------------------------------------------
    # 操作
    # ------------------------------------------------------------------

    def _do_reveal(self, x: int, y: int) -> None:
        """执行揭开操作并处理结果。"""
        assert self.board is not None
        try:
            result = self.board.reveal(x, y)
            if result == "game_over":
                return  # 主循环会渲染踩雷结果
            # result 是 Set[(x,y)]，首次点击可能揭示大片区域
            if len(result) == 1:
                coord = next(iter(result))
                cell = self.board.grid[coord[1]][coord[0]]
                print(f"  揭开 ({coord[0]},{coord[1]}) — 相邻雷: {cell.adjacent_mines}")
            else:
                print(f"  Flood fill 揭开 {len(result)} 格")
        except (IndexError, ValueError) as e:
            print(f"{_RED}  {e}{_RESET}")

    def _do_flag(self, x: int, y: int) -> None:
        """执行标记操作并显示结果。"""
        assert self.board is not None
        try:
            flagged = self.board.toggle_flag(x, y)
            status = "已标记 ⚑" if flagged else "已取消标记"
            print(f"  ({x},{y}) {status}")
        except (IndexError, ValueError) as e:
            print(f"{_RED}  {e}{_RESET}")

    # ------------------------------------------------------------------
    # 渲染
    # ------------------------------------------------------------------

    def _render(self, reveal_all: bool = False) -> None:
        """在终端绘制当前棋盘。

        Args:
            reveal_all: 若为 True，揭示所有格子（游戏结束时使用）。
        """
        assert self.board is not None
        b = self.board
        w, h = b.width, b.height

        # 清屏
        os.system("cls" if os.name == "nt" else "clear")

        # 计时器
        if not b.is_game_over and not b.check_win():
            elapsed = int(time.time() - self._start_time)
        else:
            elapsed = int(time.time() - self._start_time) if self._start_time else 0
        print(f"{_BOLD}扫雷{_RESET}  {b.width}×{b.height}  {b.mine_count}💣  "
              f"剩余: {b.width * b.height - b.mine_count - b._revealed_count}格  "
              f"⏱ {elapsed}s\n")

        # 列标头
        print("   " + "".join(f"{_GRAY}{i % 10}{_RESET}" for i in range(w)))

        # 每行
        for y in range(h):
            row_parts = [f"{_GRAY}{y:2d}{_RESET} "]
            for x in range(w):
                row_parts.append(self._cell_str(x, y, reveal_all))
            print("".join(row_parts))

    def _cell_str(self, x: int, y: int, reveal_all: bool) -> str:
        """返回单个格子的终端显示字符串。"""
        assert self.board is not None
        cell = self.board.grid[y][x]

        # 游戏结束时显示所有雷
        if reveal_all and cell.is_mine and not cell.is_revealed:
            return f"{_RED}{_MINE}{_RESET} "

        # 已揭开
        if cell.is_revealed:
            if cell.is_mine:
                return f"{_RED}{_BOLD}{_MINE}{_RESET} "
            n = cell.adjacent_mines
            if n == 0:
                return f"{_EMPTY} "
            color = _NUMBER_COLORS.get(n, "")
            return f"{color}{_BOLD}{n}{_RESET} "

        # 未揭开
        if cell.is_flagged:
            return f"{_RED}{_FLAGGED}{_RESET} "

        return f"{_CYAN}{_UNOPENED}{_RESET} "

    # ------------------------------------------------------------------
    # 帮助
    # ------------------------------------------------------------------

    @staticmethod
    def _print_help() -> None:
        """打印操作帮助。"""
        print(f"{_YELLOW}  命令格式: r x y  揭开  |  f x y  标记  |  q  退出{_RESET}")
        print(f"  {_GRAY}例: r 3 5 揭开坐标(3,5)  |  f 0 2 标记(0,2){_RESET}")

    @staticmethod
    def _print_header() -> None:
        """打印游戏标题。"""
        print(f"""
{_BOLD}  ╔══════════════════════════════╗
  ║         扫 雷 游 戏           ║
  ╚══════════════════════════════╝{_RESET}
""")


# ===================================================================
# 入口
# ===================================================================

if __name__ == "__main__":
    MinesweeperCLI().run()
