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
      page_type: overview, drill_down, data_flow, service_map, deployment
  layout.py service-map <n_services> [layer_hints...]
  layout.py service-container <n_components> [container_w]
  layout.py conditional-group <x,y,w,h> <x,y,w,h> [<x,y,w,h>...]
"""

import math
import sys

_PAGE_W   = 827
_SW_GAP   = 26
_MARGIN   = 60
_INPUT_W  = 160
_INPUT_GAP = 20
_STEP_GAP = 30
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
    valid_types = ("overview", "drill_down", "data_flow", "service_map", "deployment")
    if page_type not in valid_types:
        print(f"usage: layout.py multipage <page_type> [n_swimlanes]\n"
              f"  page_type must be one of: {', '.join(valid_types)}",
              file=sys.stderr)
        sys.exit(1)

    if page_type == "service_map" or page_type == "deployment":
        page_w, page_h, orientation = 1169, 827, "landscape"
    elif page_type == "overview" or page_type == "data_flow":
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


def cmd_service_map(n_services, *layer_hints):
    n_services = int(n_services)
    if n_services < 1 or n_services > 15:
        print("usage: layout.py service-map <n_services> [layer_hints...]\n"
              "  n_services must be between 1 and 15", file=sys.stderr)
        sys.exit(1)

    valid_layers = ("client", "gateway", "service", "worker", "infrastructure")
    layer_order = list(valid_layers)

    # Assign each service to a layer based on hints (default "service")
    assignments = []
    for i in range(n_services):
        if i < len(layer_hints) and layer_hints[i] in valid_layers:
            assignments.append(layer_hints[i])
        else:
            assignments.append("service")

    # Group services by layer, preserving order within each layer
    layers = {layer: [] for layer in layer_order}
    for i, layer in enumerate(assignments):
        layers[layer].append(i)

    # Determine active layers (those with services)
    active_layers = [l for l in layer_order if layers[l]]
    n_active = len(active_layers)
    max_in_layer = max(len(layers[l]) for l in active_layers)

    # Page dimensions: scale up for complex layouts
    # Base landscape page, but expand if needed for readability
    container_w = 200
    container_h = 140
    margin_x = 60
    margin_y = 60
    min_h_gap = 60   # minimum horizontal gap between services (space for edge labels)
    min_layer_gap = 80  # minimum vertical gap between layers (space for edge routing)

    # Compute required page dimensions
    needed_w = 2 * margin_x + max_in_layer * container_w + (max(0, max_in_layer - 1)) * min_h_gap
    needed_h = 2 * margin_y + n_active * container_h + (max(0, n_active - 1)) * min_layer_gap

    # Use at least the standard landscape size, but expand if needed
    page_w = max(1169, needed_w)
    page_h = max(827, needed_h)

    # Compute actual gaps with the final page size
    available_w = page_w - 2 * margin_x
    available_h = page_h - 2 * margin_y

    if max_in_layer > 1:
        h_gap = (available_w - max_in_layer * container_w) // (max_in_layer - 1)
    else:
        h_gap = 0

    if n_active > 1:
        layer_gap = (available_h - n_active * container_h) // (n_active - 1)
    else:
        layer_gap = 0

    print(f"page_w={page_w}")
    print(f"page_h={page_h}")
    print(f"orientation=landscape")

    # Compute positions per layer
    positions = {}  # service_index -> (x, y, layer_name)
    current_y = margin_y

    for layer_name in active_layers:
        layer_services = layers[layer_name]
        n = len(layer_services)

        if n > 1:
            total_w = n * container_w + (n - 1) * h_gap
        else:
            total_w = container_w
        start_x = (page_w - total_w) // 2

        for idx, svc_i in enumerate(layer_services):
            x = start_x + idx * (container_w + h_gap)
            positions[svc_i] = (x, current_y, layer_name)

        current_y += container_h + layer_gap

    # Output per-service positions
    for i in range(n_services):
        x, y, layer_name = positions[i]
        print(f"service[{i}]: x={x} y={y} w={container_w} h={container_h} layer={layer_name}")


def cmd_service_container(n_components, container_w=180):
    n_components = int(n_components)
    container_w = int(container_w)
    if n_components < 1 or n_components > 10:
        print("usage: layout.py service-container <n_components> [container_w]\n"
              "  n_components must be between 1 and 10", file=sys.stderr)
        sys.exit(1)

    header_h = 30
    component_h = 24
    padding = 10
    gap = 4
    component_w = container_w - 2 * padding
    first_y = header_h + 6
    container_h = header_h + 6 + n_components * component_h + (n_components - 1) * gap + padding

    print(f"container_w={container_w}")
    print(f"container_h={container_h}")
    print(f"component_w={component_w}")
    for i in range(n_components):
        y = first_y + i * (component_h + gap)
        print(f"component[{i}]: x={padding} y={y} w={component_w} h={component_h}")


def cmd_conditional_group(*service_positions):
    """Compute dashed bounding box around a set of services for conditional mode grouping."""
    if len(service_positions) < 2:
        print("usage: layout.py conditional-group <x,y,w,h> <x,y,w,h> [<x,y,w,h>...]\n"
              "  at least 2 service positions required", file=sys.stderr)
        sys.exit(1)

    padding = 20

    # Parse each position string "x,y,w,h" into a tuple of ints
    positions = []
    for pos_str in service_positions:
        parts = pos_str.split(",")
        if len(parts) != 4:
            print(f"error: invalid position '{pos_str}', expected format: x,y,w,h", file=sys.stderr)
            sys.exit(1)
        x, y, w, h = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        positions.append((x, y, w, h))

    # Compute bounding box
    min_x = min(x for x, y, w, h in positions)
    min_y = min(y for x, y, w, h in positions)
    max_x = max(x + w for x, y, w, h in positions)
    max_y = max(y + h for x, y, w, h in positions)

    # Apply padding + extra top space for label
    group_x = min_x - padding
    group_y = min_y - padding - 20  # extra 20px for label area
    group_w = (max_x - min_x) + 2 * padding
    group_h = (max_y - min_y) + 2 * padding + 20  # extra 20px for label area
    label_x = group_x + 10
    label_y = group_y + 5

    print(f"group_x={group_x}")
    print(f"group_y={group_y}")
    print(f"group_w={group_w}")
    print(f"group_h={group_h}")
    print(f"label_x={label_x}")
    print(f"label_y={label_y}")


def cmd_bidirectional_edge(src_x, src_y, src_w, src_h, tgt_x, tgt_y, tgt_w, tgt_h, offset=8):
    """Compute forward and reverse edge exit/entry points for bidirectional edges.

    Outputs decimal fractions (0.0-1.0) for exit/entry points on source and target boxes.
    Forward edge goes source->target, reverse edge goes target->source, separated by offset.
    """
    src_x = int(src_x)
    src_y = int(src_y)
    src_w = int(src_w)
    src_h = int(src_h)
    tgt_x = int(tgt_x)
    tgt_y = int(tgt_y)
    tgt_w = int(tgt_w)
    tgt_h = int(tgt_h)
    offset = int(offset)

    # Validate: source and target must not overlap
    src_right = src_x + src_w
    src_bottom = src_y + src_h
    tgt_right = tgt_x + tgt_w
    tgt_bottom = tgt_y + tgt_h

    overlaps_x = src_x < tgt_right and tgt_x < src_right
    overlaps_y = src_y < tgt_bottom and tgt_y < src_bottom

    if overlaps_x and overlaps_y:
        print(
            "usage: layout.py bidirectional-edge <src_x> <src_y> <src_w> <src_h> "
            "<tgt_x> <tgt_y> <tgt_w> <tgt_h> [offset]\n"
            "  error: source and target boxes must not overlap",
            file=sys.stderr,
        )
        sys.exit(1)

    # Determine dominant direction based on box centres
    src_cx = src_x + src_w / 2.0
    src_cy = src_y + src_h / 2.0
    tgt_cx = tgt_x + tgt_w / 2.0
    tgt_cy = tgt_y + tgt_h / 2.0

    dx = tgt_cx - src_cx
    dy = tgt_cy - src_cy

    if abs(dx) > abs(dy):
        # Horizontal dominant: edges exit from left/right sides, offset vertically
        forward_exit_y = 0.5 - (offset / src_h)
        forward_entry_y = 0.5 - (offset / tgt_h)
        reverse_exit_y = 0.5 + (offset / tgt_h)
        reverse_entry_y = 0.5 + (offset / src_h)

        if dx > 0:  # target is to the right
            fwd_exit_x = 1.0
            fwd_entry_x = 0.0
            rev_exit_x = 0.0
            rev_entry_x = 1.0
        else:  # target is to the left
            fwd_exit_x = 0.0
            fwd_entry_x = 1.0
            rev_exit_x = 1.0
            rev_entry_x = 0.0

        print(f"forward: exitX={fwd_exit_x:.4g} exitY={forward_exit_y:.4g} "
              f"entryX={fwd_entry_x:.4g} entryY={forward_entry_y:.4g}")
        print(f"reverse: exitX={rev_exit_x:.4g} exitY={reverse_exit_y:.4g} "
              f"entryX={rev_entry_x:.4g} entryY={reverse_entry_y:.4g}")
    else:
        # Vertical dominant: edges exit from top/bottom, offset horizontally
        forward_exit_x = 0.5 + (offset / src_w)
        forward_entry_x = 0.5 + (offset / tgt_w)
        reverse_exit_x = 0.5 - (offset / tgt_w)
        reverse_entry_x = 0.5 - (offset / src_w)

        if dy > 0:  # target is below
            fwd_exit_y = 1.0
            fwd_entry_y = 0.0
            rev_exit_y = 0.0
            rev_entry_y = 1.0
        else:  # target is above
            fwd_exit_y = 0.0
            fwd_entry_y = 1.0
            rev_exit_y = 1.0
            rev_entry_y = 0.0

        print(f"forward: exitX={forward_exit_x:.4g} exitY={fwd_exit_y:.4g} "
              f"entryX={forward_entry_x:.4g} entryY={fwd_entry_y:.4g}")
        print(f"reverse: exitX={reverse_exit_x:.4g} exitY={rev_exit_y:.4g} "
              f"entryX={reverse_entry_x:.4g} entryY={rev_entry_y:.4g}")


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
        "service-map":      lambda: cmd_service_map(*args),
        "service-container": lambda: cmd_service_container(*args),
        "conditional-group": lambda: cmd_conditional_group(*args),
        "bidirectional-edge": lambda: cmd_bidirectional_edge(*args),
    }
    fn = dispatch.get(cmd)
    if fn is None:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
    fn()


if __name__ == "__main__":
    main()
