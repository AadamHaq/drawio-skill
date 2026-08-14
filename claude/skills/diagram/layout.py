#!/usr/bin/env python3
"""Coordinate calculator for the diagram skill. No third-party packages required.

Usage:
  layout.py swimlanes <n>
  layout.py inputs <n>                        (also: outputs <n>)
  layout.py steps <sw_w> <startSize> <lines_per_step...>
  layout.py split <sw_w> <last_step_y> <last_step_h> [split_gap]
  layout.py check-approach <last_wx> <last_wy> <tx> <ty> <tw> <th> <entry_x> <entry_y>
  layout.py nested-container <parent_sw_w> <parent_start_y> <n_children> <lines_per_child...>
  layout.py loop-annotation <first_node_y> <last_node_y> <last_node_h> <sw_w>
  layout.py n-split <sw_w> <last_step_y> <last_step_h> <n_outcomes> [split_gap]
  layout.py multipage <page_type> [n_swimlanes]
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


def cmd_loop_annotation(first_node_y, last_node_y, last_node_h, sw_w):
    # Validate all args are positive integers
    try:
        first_node_y = int(first_node_y)
        last_node_y = int(last_node_y)
        last_node_h = int(last_node_h)
        sw_w = int(sw_w)
    except (ValueError, TypeError):
        print("usage: layout.py loop-annotation <first_node_y> <last_node_y> <last_node_h> <sw_w>", file=sys.stderr)
        print("  all arguments must be positive integers", file=sys.stderr)
        sys.exit(1)
    if first_node_y <= 0 or last_node_y <= 0 or last_node_h <= 0 or sw_w <= 0:
        print("usage: layout.py loop-annotation <first_node_y> <last_node_y> <last_node_h> <sw_w>", file=sys.stderr)
        print("  all arguments must be positive integers", file=sys.stderr)
        sys.exit(1)

    annotation_y = first_node_y - 15 - 20  # 15px padding + 20px label area
    annotation_bottom = last_node_y + last_node_h + 15
    annotation_h = annotation_bottom - annotation_y
    annotation_w = sw_w - 8  # 4px margin each side
    annotation_x = 4

    label_x = annotation_x + annotation_w - 10
    label_y = annotation_y + 5

    print(f"annotation_x={annotation_x}")
    print(f"annotation_y={annotation_y}")
    print(f"annotation_w={annotation_w}")
    print(f"annotation_h={annotation_h}")
    print(f"label_x={label_x}")
    print(f"label_y={label_y}")


def cmd_nested_container(parent_sw_w, parent_start_y, n_children, *lines_per_child):
    parent_sw_w = int(parent_sw_w)
    parent_start_y = int(parent_start_y)
    n_children = int(n_children)

    if parent_sw_w < 100:
        print("error: parent_sw_w must be >= 100", file=sys.stderr)
        sys.exit(1)

    if len(lines_per_child) < n_children:
        print(
            f"usage: layout.py nested-container <parent_sw_w> <parent_start_y> <n_children> <lines...>\n"
            f"  expected {n_children} line counts but got {len(lines_per_child)}",
            file=sys.stderr,
        )
        sys.exit(1)

    container_x = 12
    container_y = parent_start_y
    container_w = parent_sw_w - 24
    child_step_w = parent_sw_w - 60
    child_step_x = 18

    print(f"container_x={container_x}  container_y={container_y}  container_w={container_w}")
    print(f"child_step_w={child_step_w}  child_step_x={child_step_x}")

    y = 20  # header area
    for i in range(n_children):
        lines = int(lines_per_child[i])
        h = max(36, 22 + lines * 18)
        print(f"child[{i}]: y={y}  h={h}")
        if i < n_children - 1:
            y += h + _STEP_GAP
        else:
            y += h

    container_h = y + 20  # bottom padding
    print(f"container_h={container_h}")


def cmd_n_split(sw_w, last_step_y, last_step_h, n_outcomes, split_gap=50):
    sw_w = int(sw_w)
    last_step_y = int(last_step_y)
    last_step_h = int(last_step_h)
    n = int(n_outcomes)
    split_gap = int(split_gap)
    if n < 2:
        print("n-split: n_outcomes must be >= 2", file=sys.stderr)
        sys.exit(1)
    step_w = sw_w - 36
    split_y = last_step_y + last_step_h + split_gap
    box_w = math.floor((step_w - (n - 1) * 10) / n)
    print(f"split_y={split_y}")
    for i in range(n):
        x = 18 + i * (box_w + 10)
        print(f"outcome[{i}]: x={x}  w={box_w}")
    sl_height = split_y + _SPLIT_H + 20
    print(f"sl_height={sl_height}")


def cmd_multipage(page_type, n_swimlanes=None):
    valid_types = ("overview", "drill_down", "data_flow")
    if page_type not in valid_types:
        print(f"usage: layout.py multipage <page_type> [n_swimlanes]\n"
              f"  page_type must be one of: {', '.join(valid_types)}",
              file=sys.stderr)
        sys.exit(1)

    if page_type == "overview" or page_type == "data_flow":
        page_w, page_h, orientation = 827, 1169, "portrait"
    else:
        # drill_down
        lanes = int(n_swimlanes) if n_swimlanes is not None else 1
        if lanes >= 4:
            page_w, page_h, orientation = 1169, 827, "landscape"
        else:
            page_w, page_h, orientation = 827, 1169, "portrait"

    print(f"page_w={page_w}")
    print(f"page_h={page_h}")
    print(f"orientation={orientation}")


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
        "swimlanes":        lambda: cmd_swimlanes(*args),
        "inputs":           lambda: cmd_inputs(*args),
        "outputs":          lambda: cmd_inputs(*args),
        "steps":            lambda: cmd_steps(*args),
        "split":            lambda: cmd_split(*args),
        "check-approach":   lambda: cmd_check_approach(*args),
        "nested-container": lambda: cmd_nested_container(*args),
        "loop-annotation":  lambda: cmd_loop_annotation(*args),
        "n-split":          lambda: cmd_n_split(*args),
        "multipage":        lambda: cmd_multipage(*args),
    }
    fn = dispatch.get(cmd)
    if fn is None:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
    fn()


if __name__ == "__main__":
    main()
