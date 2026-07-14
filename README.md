# 扫雷 Minesweeper

Python 扫雷游戏，支持命令行和 Pygame 图形界面两种模式。

## 项目结构

```
src/minesweeper/
├── core.py         # 游戏引擎（棋盘、布雷、胜负判定）
├── cli.py          # 命令行版（ANSI 彩色）
└── gui_pygame.py   # 图形界面版（Pygame，鼠标操作）
```

## 运行

```bash
# 安装依赖
pip install pygame

# 命令行版
cd src
python minesweeper/cli.py

# 图形界面版
cd src
python minesweeper/gui_pygame.py
```

## 玩法

- **左键** 揭开格子 / **右键** 标记地雷
- 首次点击必定安全
- 数字表示周围 8 格中的地雷数
- 揭开所有非雷格子即为胜利
