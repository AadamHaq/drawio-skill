#!/usr/bin/env python3
"""Coordinate calculator for the diagram skill. No third-party packages required.

Usage:
  layout.py swimlanes <n>
  layout.py inputs <n>                        (also: outputs <n>)
  layout.py steps <sw_w> <startSize> <lines_per_step...>
  layout.py split <sw_w> <last_step_y> <last_step_h> [split_gap]
  layout.py check-approach <last_wx> <last_wy> <tx> <ty> <tw> <th> <entry_x> <entry_y>
"""

import math
import sys

_PAGE_W   = 827
_SW_GAP   = 26
_MARGIN   = 60
_INPUT_W  = 160
_INPUT_GAP = 20
_STEP_GAP = 16
_SPLIT_H  = 36


def cmd_swimlanes(n):
    n = int(n)
    sw_w = min(316, math.floor((_PAGE_W - _MARGIN - (n - 1) * _SW_GAP) / n))
    step_w = sw_w - 36
    total_w = n * sw_w + (n - 1) * _SW_GAP
    first_sl_x = math.floor((_PAGE_W - total_w) / 2)
    print(f"sw_w={sw_w}")
    print(f"step_w={step_w}")
    print(f"total_w={total_w}")
    print(f"first_sl_x={first_sl_x}")
    for i in range(n):
        print(f"sl_x[{i}]={first_sl_x + i * (sw_w + _SW_GAP)}")


def cmd_inputs(n):
    n = int(n)
    total_w = n * _INPUT_W + (n - 1) * _INPUT_GAP
    first_x = math.floor((_PAGE_W - total_w) / 2)
    print(f"total_w={total_w}")
    print(f"first_x={first_x}")
    for i in range(n):
        print(f"x[{i}]={first_x + i * (_INPUT_W + _INPUT_GAP)}")


def cmd_steps(sw_w, start_size, *line_counts):
    sw_w = int(sw_w)
    start_size = int(start_size)
    step_w = sw_w - 36
    first_y = start_size + 15
    print(f"step_w={step_w}")
    print(f"first_step_y={first_y}  (startSize={start_size})")
    y = first_y
    for i, lines in enumerate(line_counts):
        h = max(36, 22 + int(lines) * 18)
        print(f"step[{i}]: y={y}  h={h}  (lines={lines})")
        y += h + _STEP_GAP
    last_bottom = y - _STEP_GAP
    print(f"last_bottom={last_bottom}  (rel to swimlane)")
    print(f"sl_height_no_split={last_bottom + 20}")


def cmd_split(sw_w, last_step_y, last_step_h, split_gap=50):
    sw_w = int(sw_w)
    step_w = sw_w - 36
    split_y = int(last_step_y) + int(last_step_h) + int(split_gap)
    pass_w = math.floor((step_w - 10) / 2)
    fail_x = 18 + pass_w + 10
    fail_w = step_w - pass_w - 10
    sl_height = split_y + _SPLIT_H + 20
    print(f"split_y={split_y}  (rel to swimlane)")
    print(f"pass_x=18  pass_w={pass_w}")
    print(f"fail_x={fail_x}  fail_w={fail_w}")
    print(f"sl_height={sl_height}")


def cmd_check_approach(last_wx, last_wy, tx, ty, tw, th, entry_x, entry_y):
    last_wx, last_wy = float(last_wx), float(last_wy)
    tx, ty, tw, th = float(tx), float(ty), float(tw), float(th)
    entry_x, entry_y = float(entry_x), float(entry_y)
    ok = True
    if entry_y == 0 and last_wy > ty - 20:
        print(f"FAIL entryY=0: last_wy={last_wy} must be <= {ty - 20:.0f}  (target_top={ty:.0f} - 20)")
        ok = False
    if entry_y == 1 and last_wy < ty + th + 20:
        print(f"FAIL entryY=1: last_wy={last_wy} must be >= {ty + th + 20:.0f}  (target_bottom={ty + th:.0f} + 20)")
        ok = False
    if entry_x == 0 and last_wx > tx - 20:
        print(f"FAIL entryX=0: last_wx={last_wx} must be <= {tx - 20:.0f}  (target_left={tx:.0f} - 20)")
        ok = False
    if entry_x == 1 and last_wx < tx + tw + 20:
        print(f"FAIL entryX=1: last_wx={last_wx} must be >= {tx + tw + 20:.0f}  (target_right={tx + tw:.0f} + 20)")
        ok = False
    if ok:
        print("OK")


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)
    cmd, args = sys.argv[1], sys.argv[2:]
    dispatch = {
        "swimlanes":     lambda: cmd_swimlanes(*args),
        "inputs":        lambda: cmd_inputs(*args),
        "outputs":       lambda: cmd_inputs(*args),
        "steps":         lambda: cmd_steps(*args),
        "split":         lambda: cmd_split(*args),
        "check-approach": lambda: cmd_check_approach(*args),
    }
    fn = dispatch.get(cmd)
    if fn is None:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
    fn()


if __name__ == "__main__":
    main()
