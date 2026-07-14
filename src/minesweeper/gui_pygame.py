"""
扫雷图形界面 — 基于 Pygame + core.py。

运行::

    python gui_pygame.py      # 从 src/ 目录运行

依赖::

    pip install pygame
"""

from __future__ import annotations

import os
import sys
from typing import Optional, Tuple

# 确保能 import minesweeper.core
_here = os.path.dirname(os.path.abspath(__file__))
_src = os.path.dirname(_here) if os.path.basename(_here) == "minesweeper" else _here
if _src not in sys.path:
    sys.path.insert(0, _src)

import pygame
from minesweeper.core import Board

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

CELL_SIZE = 40          # 格子像素大小
BORDER = 2              # 凸起边框厚度
FONT_SIZE = 24          # 数字字号
HEADER_HEIGHT = 60      # 顶部信息栏高度

# 颜色
BG_COLOR       = (180, 180, 180)
UNOPENED_COLOR = (200, 200, 200)
REVEALED_COLOR = (220, 220, 220)
MINE_BG_COLOR  = (255, 100, 100)   # 踩雷格子背景
HIGHLIGHT      = (255, 255, 255)   # 凸起高光
SHADOW         = (100, 100, 100)   # 凸起阴影

NUMBER_COLORS: dict[int, tuple[int, int, int]] = {
    1: (0,   0,   255),   # 蓝
    2: (0,   128, 0),     # 绿
    3: (255, 0,   0),     # 红
    4: (0,   0,   128),   # 深蓝
    5: (128, 0,   0),     # 深红
    6: (0,   128, 128),   # 青
    7: (0,   0,   0),     # 黑
    8: (128, 128, 128),   # 灰
}

# 难度预设
PRESETS = {
    "1": ("初级", 9, 9, 10),
    "2": ("中级", 16, 16, 40),
    "3": ("高级", 30, 16, 99),
}

DEFAULT_DIFFICULTY = "1"  # 默认初级


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _safe_font(size: int, bold: bool = False) -> pygame.font.Font:
    """安全获取中文字体——直接加载字体文件，绕开 pygame SysFont 的 bug。"""
    font_paths = [
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", f)
        for f in ("simsun.ttc", "msyh.ttc", "simhei.ttf", "simkai.ttf")
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except Exception:
                continue
    # 最后的兜底（不支持中文，但不会崩）
    return pygame.font.Font(None, size)


# ---------------------------------------------------------------------------
# GUI 类
# ---------------------------------------------------------------------------

class MinesweeperGUI:
    """扫雷 Pygame 图形界面。"""

    def __init__(self, width: int, height: int, mine_count: int) -> None:
        self.board = Board(width, height, mine_count)
        self.cell_size = CELL_SIZE
        self.header = HEADER_HEIGHT

        # 窗口尺寸（自动适应棋盘）
        win_w = width * self.cell_size
        win_h = height * self.cell_size + self.header

        self.screen = pygame.display.set_mode((win_w, win_h))
        pygame.display.set_caption("扫雷")

        self.clock = pygame.time.Clock()
        self._font = _safe_font(FONT_SIZE, bold=True)
        self._header_font = _safe_font(20)
        self._small_font = _safe_font(28)

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    def run(self) -> None:
        """进入游戏主循环。"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_click(event)

            self._draw()
            self.clock.tick(60)  # 60 FPS

        pygame.quit()

    # ------------------------------------------------------------------
    # 鼠标处理
    # ------------------------------------------------------------------

    def _handle_click(self, event: pygame.event.Event) -> None:
        """将鼠标坐标转换为棋盘坐标并分派操作。"""
        mx, my = event.pos  # 屏幕坐标

        # 检查是否在棋盘区域内
        if my < self.header:
            return

        gx = mx // self.cell_size
        gy = (my - self.header) // self.cell_size

        # 坐标越界检查
        if not (0 <= gx < self.board.width and 0 <= gy < self.board.height):
            return

        try:
            if event.button == 1:        # 左键 → 揭开
                self.board.reveal(gx, gy)
            elif event.button == 3:      # 右键 → 标记
                self.board.toggle_flag(gx, gy)
        except (IndexError, ValueError):
            pass  # 忽略无效操作（已揭开/已标记/越界等）

        # 检查胜负（仅在操作后检查）
        self._check_endgame()

    def _check_endgame(self) -> None:
        """弹窗提示游戏结束或胜利。"""
        if self.board.is_game_over:
            self._draw()
            pygame.display.flip()
            self._show_message("💣 游戏结束！")
            self._restart()
        elif self.board.check_win():
            self._draw()
            pygame.display.flip()
            self._show_message("🎉 恭喜获胜！")
            self._restart()

    def _show_message(self, text: str) -> None:
        """简单的游戏内弹窗，等待按键或点击关闭。"""
        w, h = self.screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        # 文字
        lines = text.split("\n")
        rendered_lines = [self._small_font.render(line, True, (255, 255, 255)) for line in lines]
        total_h = sum(r.get_height() for r in rendered_lines) + (len(lines) - 1) * 4
        y0 = (h - total_h) // 2
        for r in rendered_lines:
            x = (w - r.get_width()) // 2
            self.screen.blit(r, (x, y0))
            y0 += r.get_height() + 4

        pygame.display.flip()

        # 等待用户操作
        waiting = True
        while waiting:
            for evt in pygame.event.get():
                if evt.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.QUIT):
                    waiting = False

    def _restart(self) -> None:
        """重置棋盘，保留当前难度。"""
        self.board = Board(self.board.width, self.board.height, self.board.mine_count)

    # ------------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        """绘制整个画面：背景 → 信息栏 → 棋盘。"""
        self.screen.fill(BG_COLOR)
        self._draw_header()
        self._draw_board()
        pygame.display.flip()

    def _draw_header(self) -> None:
        """绘制顶部信息栏。"""
        b = self.board
        total = b.width * b.height - b.mine_count - b._revealed_count
        text = f"扫雷  {b.width}×{b.height}  💣{b.mine_count}  剩余: {total}格"
        surf = self._header_font.render(text, True, (0, 0, 0))
        self.screen.blit(surf, (8, 10))

        # 帮助提示
        help_text = "左键揭开 | 右键标记 | ESC 退出"
        help_surf = self._small_font.render(help_text, True, (80, 80, 80))
        self.screen.blit(help_surf, (8, 34))

    def _draw_board(self) -> None:
        """遍历绘制所有格子。"""
        b = self.board
        for y in range(b.height):
            for x in range(b.width):
                cell = b.grid[y][x]
                px = x * self.cell_size
                py = self.header + y * self.cell_size
                self._draw_cell(px, py, cell, is_dead=b.is_game_over)

    def _draw_cell(
        self,
        px: int,
        py: int,
        cell,
        is_dead: bool,
    ) -> None:
        """绘制单个格子。"""
        r = pygame.Rect(px, py, self.cell_size, self.cell_size)

        if cell.is_revealed:
            # 背景
            if cell.is_mine:
                # 踩雷的格子用红色背景
                pygame.draw.rect(self.screen, MINE_BG_COLOR, r)
            else:
                pygame.draw.rect(self.screen, REVEALED_COLOR, r)

            # 内容
            if cell.is_mine:
                self._draw_mine(px, py)
            elif cell.adjacent_mines > 0:
                self._draw_number(px, py, cell.adjacent_mines)
        else:
            # 未揭开：灰色凸起方块
            self._draw_raised_rect(px, py)

            # 标记
            if cell.is_flagged:
                if is_dead and not cell.is_mine:
                    # 游戏结束时标记错误的格子标个叉
                    self._draw_flag(px, py)
                    self._draw_wrong(px, py)
                else:
                    self._draw_flag(px, py)

        # 游戏结束后显示所有未标记的地雷
        if is_dead and cell.is_mine and not cell.is_revealed and not cell.is_flagged:
            pygame.draw.rect(self.screen, REVEALED_COLOR, r)
            self._draw_mine(px, py)

    def _draw_raised_rect(self, px: int, py: int) -> None:
        """绘制凸起立体方块。"""
        s = self.cell_size
        # 主体
        pygame.draw.rect(self.screen, UNOPENED_COLOR, (px, py, s, s))
        # 上边 + 左边高光
        pygame.draw.line(self.screen, HIGHLIGHT, (px, py + s - 1), (px, py), BORDER)
        pygame.draw.line(self.screen, HIGHLIGHT, (px, py), (px + s - 1, py), BORDER)
        # 下边 + 右边阴影
        pygame.draw.line(self.screen, SHADOW, (px + 1, py + s - 1),
                         (px + s - 1, py + s - 1), BORDER)
        pygame.draw.line(self.screen, SHADOW, (px + s - 1, py + s - 1),
                         (px + s - 1, py), BORDER)

    def _draw_mine(self, px: int, py: int) -> None:
        """在格子中央画地雷（黑色圆 + 引信线）。"""
        cx, cy = px + self.cell_size // 2, py + self.cell_size // 2
        r = self.cell_size // 3
        # 黑色实心圆
        pygame.draw.circle(self.screen, (0, 0, 0), (cx, cy), r)
        # 高光让圆有立体感
        pygame.draw.circle(self.screen, (60, 60, 60), (cx - r // 3, cy - r // 3), r // 3)
        # 引信线
        pygame.draw.line(self.screen, (0, 0, 0), (cx, cy - r), (cx, py + 3), 2)
        pygame.draw.line(self.screen, (0, 0, 0), (cx, py + 3), (cx - 3, py - 2), 2)

    def _draw_flag(self, px: int, py: int) -> None:
        """在格子中央画旗子。"""
        cx, cy = px + self.cell_size // 2, py + self.cell_size // 2
        r = self.cell_size // 3
        # 旗杆
        flag_top = cy - r
        flag_bottom = cy + r
        pygame.draw.line(self.screen, (0, 0, 0), (cx + r // 2, flag_top),
                         (cx + r // 2, flag_bottom), 3)
        # 底座
        pygame.draw.rect(self.screen, (0, 0, 0),
                         (cx - r // 2, flag_bottom - 2, r * 2, 4))
        # 红旗
        tri = [(cx + r // 2 - 1, flag_top),
               (cx - r, cy - 2),
               (cx + r // 2 - 1, cy + r // 2)]
        pygame.draw.polygon(self.screen, (220, 30, 30), tri)
        pygame.draw.polygon(self.screen, (0, 0, 0), tri, 1)

    def _draw_wrong(self, px: int, py: int) -> None:
        """在错误标记的格子上画叉。"""
        s = self.cell_size
        margin = 6
        pygame.draw.line(self.screen, (200, 0, 0),
                         (px + margin, py + margin),
                         (px + s - margin, py + s - margin), 3)
        pygame.draw.line(self.screen, (200, 0, 0),
                         (px + s - margin, py + margin),
                         (px + margin, py + s - margin), 3)

    def _draw_number(self, px: int, py: int, n: int) -> None:
        """在格子中央绘制数字。"""
        color = NUMBER_COLORS.get(n, (0, 0, 0))
        text = self._font.render(str(n), True, color)
        tx = px + (self.cell_size - text.get_width()) // 2
        ty = py + (self.cell_size - text.get_height()) // 2
        self.screen.blit(text, (tx, ty))


# ---------------------------------------------------------------------------
# 难度选择
# ---------------------------------------------------------------------------

def _choose_difficulty() -> Tuple[int, int, int]:
    """控制台选择难度，返回 (width, height, mine_count)。"""
    print("请选择难度：")
    print("  1. 初级  (9×9,  10 雷)")
    print("  2. 中级  (16×16, 40 雷)")
    print("  3. 高级  (30×16, 99 雷)")
    print("  4. 自定义")
    choice = input(">>> ").strip()
    if choice in PRESETS:
        _, w, h, m = PRESETS[choice]
        return w, h, m
    elif choice == "4":
        w = int(input("宽度 (5-50): "))
        h = int(input("高度 (5-30): "))
        m = int(input("雷数: "))
        return w, h, m
    else:
        # 默认初级
        _, w, h, m = PRESETS[DEFAULT_DIFFICULTY]
        return w, h, m


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main() -> None:
    """初始化 Pygame → 选难度 → 进入游戏循环。"""
    pygame.init()

    # 命令行选择难度
    print("\n" + "=" * 40)
    print("  扫雷 — Pygame 图形界面版")
    print("=" * 40 + "\n")
    width, height, mine_count = _choose_difficulty()
    print(f"\n启动 {width}×{height}, {mine_count} 雷...\n")

    gui = MinesweeperGUI(width, height, mine_count)
    gui.run()


if __name__ == "__main__":
    main()
