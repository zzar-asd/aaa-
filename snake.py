#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贪吃蛇小程序（终端版，仅使用 Python 标准库 curses）

运行方式:
    python3 snake.py

操作说明:
    方向键 / WASD : 控制蛇的移动方向
    p             : 暂停 / 继续
    r             : 游戏结束后重新开始
    q             : 退出游戏

吃到食物 +10 分，每吃 5 个食物速度加快一档。
撞墙或撞到自己则游戏结束。
"""

import curses
import random
import time

# 游戏区域大小（不含边框与顶部状态栏）
BOARD_WIDTH = 30
BOARD_HEIGHT = 20

INITIAL_DELAY = 0.15   # 初始每步间隔（秒）
MIN_DELAY = 0.05       # 最快速度
SPEED_UP_EVERY = 5     # 每吃 N 个食物提速一次
SPEED_STEP = 0.01      # 每次提速减少的间隔

DIRS = {
    curses.KEY_UP: (-1, 0),
    curses.KEY_DOWN: (1, 0),
    curses.KEY_LEFT: (0, -1),
    curses.KEY_RIGHT: (0, 1),
    ord('w'): (-1, 0),
    ord('s'): (1, 0),
    ord('a'): (0, -1),
    ord('d'): (0, 1),
    ord('W'): (-1, 0),
    ord('S'): (1, 0),
    ord('A'): (0, -1),
    ord('D'): (0, 1),
}


def place_food(snake):
    """在空白处随机放置食物"""
    empty = [
        (y, x)
        for y in range(1, BOARD_HEIGHT + 1)
        for x in range(1, BOARD_WIDTH + 1)
        if (y, x) not in snake
    ]
    return random.choice(empty)


def draw_board(win):
    """绘制边框和背景"""
    win.erase()
    win.box()
    status = " 贪吃蛇 | 方向键/WASD移动 | P暂停 | Q退出 "
    win.addstr(0, max(1, (BOARD_WIDTH + 2 - len(status)) // 2), status[:BOARD_WIDTH])


def game_over_screen(win, score):
    """显示游戏结束画面，返回 True 表示重开，False 表示退出"""
    msg1 = f" 游戏结束！得分: {score} "
    msg2 = " R-重新开始  Q-退出 "
    cy = BOARD_HEIGHT // 2 + 1
    cx = BOARD_WIDTH // 2
    win.addstr(cy, max(1, cx - len(msg1) // 2), msg1, curses.A_BOLD | curses.A_BLINK)
    win.addstr(cy + 2, max(1, cx - len(msg2) // 2), msg2)
    win.refresh()
    win.nodelay(False)
    while True:
        key = win.getch()
        if key in (ord('r'), ord('R')):
            return True
        if key in (ord('q'), ord('Q')):
            return False


def run_game(stdscr):
    """一局游戏的完整流程，返回 False 表示用户请求退出程序"""
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    # 初始化颜色
    has_color = curses.has_colors()
    if has_color:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)   # 蛇身
        curses.init_pair(2, curses.COLOR_RED, -1)     # 食物
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # 蛇头

    snake_head_attr = curses.color_pair(1) | curses.A_BOLD if has_color else curses.A_BOLD
    snake_body_attr = curses.color_pair(1) if has_color else 0
    food_attr = curses.color_pair(2) | curses.A_BOLD if has_color else curses.A_BOLD

    # 蛇初始位置：水平居中，向右移动
    start_y = BOARD_HEIGHT // 2
    start_x = BOARD_WIDTH // 4
    snake = [(start_y, start_x + i) for i in range(3)][::-1]  # 头部在前
    direction = (0, 1)
    pending_dir = direction

    score = 0
    eaten = 0
    delay = INITIAL_DELAY
    food = place_food(snake)
    paused = False

    while True:
        # -------- 输入处理 --------
        key = stdscr.getch()
        if key in (ord('q'), ord('Q')):
            return False
        if key in (ord('p'), ord('P')):
            paused = not paused
        elif key in DIRS:
            new_dir = DIRS[key]
            # 禁止直接反向
            if (new_dir[0] + direction[0], new_dir[1] + direction[1]) != (0, 0):
                pending_dir = new_dir

        if paused:
            stdscr.addstr(0, BOARD_WIDTH - 8, " 已暂停 ", curses.A_REVERSE)
            stdscr.refresh()
            time.sleep(0.05)
            continue

        # -------- 逻辑更新 --------
        direction = pending_dir
        head_y, head_x = snake[0]
        new_head = (head_y + direction[0], head_x + direction[1])

        # 撞墙检测
        if not (1 <= new_head[0] <= BOARD_HEIGHT and 1 <= new_head[1] <= BOARD_WIDTH):
            draw_board(stdscr)
            stdscr.addstr(1, 2, f" 得分: {score} ", snake_head_attr)
            if game_over_screen(stdscr, score):
                return True  # 重开
            return False

        # 撞自己检测（尾巴这一步会移走，所以排除最后一个节点）
        if new_head in snake[:-1]:
            draw_board(stdscr)
            stdscr.addstr(1, 2, f" 得分: {score} ", snake_head_attr)
            if game_over_screen(stdscr, score):
                return True
            return False

        snake.insert(0, new_head)

        if new_head == food:
            score += 10
            eaten += 1
            if eaten % SPEED_UP_EVERY == 0:
                delay = max(MIN_DELAY, delay - SPEED_STEP * SPEED_UP_EVERY)
            food = place_food(snake)
        else:
            snake.pop()

        # -------- 绘制 --------
        draw_board(stdscr)
        stdscr.addstr(1, 2, f" 得分: {score}  长度: {len(snake)}  速度: {INITIAL_DELAY / delay:.1f}x ",
                      snake_head_attr)

        hy, hx = snake[0]
        stdscr.addch(hy, hx, '@', snake_head_attr)
        for y, x in snake[1:]:
            stdscr.addch(y, x, 'o', snake_body_attr)
        fy, fx = food
        stdscr.addch(fy, fx, '*', food_attr)

        stdscr.refresh()
        time.sleep(delay)


def main(stdscr):
    while True:
        restart = run_game(stdscr)
        if not restart:
            break


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    print("感谢游玩贪吃蛇！再见~")
