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
  layout.py palette [role]                    (show colour pairs by semantic role)
  layout.py layers <n_layers> [items_per_layer...]
  layout.py boilerplate <page_name> [page_name...]
  layout.py legend <lowest_y> [topology]      (pipeline|microservice|layered)
  layout.py step-height "Label<br/>Line 2"    (compute box height from label)
  layout.py shared-layer <n_items> [y] [page_w]
  layout.py scaffold <topology> [n_stages]    (pipeline|microservice|layered)
"""

import math
import sys

_PAGE_W   = 827
_SW_GAP   = 40
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
    first_y = start_size + 26
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


# ─── Colour palette ──────────────────────────────────────────────────────────

# Standard draw.io default palette — pastel fill + saturated stroke of same hue.
_PALETTE = {
    "config":       {"fill": "#dae8fc", "stroke": "#6c8ebf", "name": "Light Blue"},
    "input":        {"fill": "#dae8fc", "stroke": "#6c8ebf", "name": "Light Blue"},
    "generator":    {"fill": "#fff2cc", "stroke": "#d6b656", "name": "Light Yellow"},
    "process":      {"fill": "#fff2cc", "stroke": "#d6b656", "name": "Light Yellow"},
    "validator":    {"fill": "#d5e8d4", "stroke": "#82b366", "name": "Light Green"},
    "postprocess":  {"fill": "#e1d5e7", "stroke": "#9673a6", "name": "Light Purple"},
    "environment":  {"fill": "#f8cecc", "stroke": "#b85450", "name": "Light Red"},
    "domain":       {"fill": "#f8cecc", "stroke": "#b85450", "name": "Light Red"},
    "env_container": {"fill": "#fef5f5", "stroke": "#b85450", "name": "Very Light Red (dashed container)"},
    "submodule":    {"fill": "#ffffff", "stroke": "#b85450", "name": "White/Red border"},
    "lane_bg":      {"fill": "#f5f5f5", "stroke": "#666666", "name": "Neutral grey"},
    "lane_header":  {"fill": "#f0f0f0", "stroke": "#999999", "name": "Darker grey"},
    "output":       {"fill": "#d5e8d4", "stroke": "#82b366", "name": "Light Green"},
    "fail":         {"fill": "#f8cecc", "stroke": "#b85450", "name": "Light Red"},
    "pass":         {"fill": "#d5e8d4", "stroke": "#82b366", "name": "Light Green"},
    "neutral":      {"fill": "#fff4e6", "stroke": "#d79b00", "name": "Light Orange"},
    "step":         {"fill": "#ffffff", "stroke": "inherit", "name": "White (use parent stroke)"},
}


def cmd_palette(*args):
    """Output draw.io colour pairs by semantic role. Optionally filter to a single role."""
    if args:
        role = args[0].lower()
        if role in _PALETTE:
            p = _PALETTE[role]
            print(f"fillColor={p['fill']};strokeColor={p['stroke']};  # {p['name']}")
        else:
            print(f"unknown role: {role}", file=sys.stderr)
            print(f"available: {', '.join(sorted(_PALETTE.keys()))}", file=sys.stderr)
            sys.exit(1)
    else:
        # Print all roles grouped by colour
        print("# Semantic colour palette (draw.io defaults)")
        print("# Paste fill+stroke into style strings")
        print()
        for role, p in _PALETTE.items():
            print(f"{role:14s}  fill={p['fill']}  stroke={p['stroke']}  ({p['name']})")


# ─── Layer layout ────────────────────────────────────────────────────────────

def cmd_layers(n_layers, *items_per_layer):
    """Compute horizontal band positions for a layered architecture diagram.

    Layers are full-width bands stacked top-to-bottom. Each layer can contain
    N items arranged in a row within it.

    Args:
        n_layers: number of horizontal bands
        items_per_layer: optional count of items in each layer (default 1 each)
    """
    n_layers = int(n_layers)
    if n_layers < 1 or n_layers > 10:
        print("usage: layout.py layers <n_layers> [items_per_layer...]\n"
              "  n_layers must be between 1 and 10", file=sys.stderr)
        sys.exit(1)

    # Parse items per layer (default 1)
    items = []
    for i in range(n_layers):
        if i < len(items_per_layer):
            items.append(int(items_per_layer[i]))
        else:
            items.append(1)

    page_w = 827
    margin_x = 30
    margin_y = 30
    layer_gap = 20
    item_gap = 50  # minimum 50px for edge labels between items
    item_padding = 18  # padding inside layer band around items

    # Check if we need a wider page to fit items at 240px with 50px gaps
    max_items_in_layer = max(items)
    target_item_w = 240
    needed_page_w = 2 * margin_x + 2 * item_padding + max_items_in_layer * target_item_w + (max_items_in_layer - 1) * item_gap
    if needed_page_w > page_w:
        page_w = ((needed_page_w + 9) // 10) * 10  # round up to nearest 10
        print(f"# Page auto-widened to {page_w}px to fit {max_items_in_layer} items at 240px + 50px gaps")

    # Layer band width is full page minus margins
    band_w = page_w - 2 * margin_x
    # Layer heights: scale with item count (more items = taller to fit labels)
    base_layer_h = 80
    per_item_extra = 20  # extra height if layer has many items (rows)

    # Compute total height to see if we need landscape
    total_h = 2 * margin_y + sum(
        base_layer_h + (max(0, items[i] - 3) * per_item_extra)
        for i in range(n_layers)
    ) + (n_layers - 1) * layer_gap

    orientation = "portrait"
    page_h = 1169
    if total_h > 1100:
        orientation = "landscape"
        page_w = 1169
        page_h = 827
        band_w = page_w - 2 * margin_x

    print(f"page_w={page_w}")
    print(f"page_h={page_h}")
    print(f"orientation={orientation}")
    print(f"band_w={band_w}")
    print()

    y = margin_y
    for i in range(n_layers):
        n_items = items[i]
        layer_h = base_layer_h + max(0, n_items - 3) * per_item_extra
        print(f"layer[{i}]: x={margin_x} y={y} w={band_w} h={layer_h}")

        # Compute item positions within this layer
        # Target width: 240px (fits ~40 chars). Auto-computed from available space.
        max_item_w = 240
        needed_w = n_items * max_item_w + (n_items - 1) * item_gap + 2 * item_padding
        if needed_w > band_w:
            # Items don't fit at 240px — shrink to fit but warn
            item_w = (band_w - 2 * item_padding - (n_items - 1) * item_gap) // max(1, n_items)
            if item_w < 200:
                print(f"  # WARNING: items at {item_w}px (< 200). Consider wider page or fewer items.")
        else:
            item_w = max_item_w
        items_total_w = n_items * item_w + (n_items - 1) * item_gap
        first_item_x = (band_w - items_total_w) // 2  # centred within band
        item_y = 30  # relative to layer (below header)
        item_h = layer_h - 30 - 10  # fill available height minus header and bottom pad

        for j in range(n_items):
            ix = first_item_x + j * (item_w + item_gap)
            print(f"  item[{i},{j}]: x={ix} y={item_y} w={item_w} h={item_h}  (relative to layer)")

        y += layer_h + layer_gap
        print()

    print(f"total_h={y - layer_gap + margin_y}")


# ─── Multi-page boilerplate ──────────────────────────────────────────────────

def cmd_boilerplate(*page_names):
    """Output the mxfile XML skeleton for multi-page diagrams."""
    if not page_names:
        print("usage: layout.py boilerplate <page_name> [page_name...]", file=sys.stderr)
        sys.exit(1)

    print('<?xml version="1.0" encoding="UTF-8"?>')
    print('<mxfile host="ac.draw.io">')
    for i, name in enumerate(page_names):
        page_id = f"page-{i}"
        # Default portrait; service-map/deployment pages get landscape
        is_landscape = any(kw in name.lower() for kw in ("service", "deploy", "map"))
        pw, ph = (1169, 827) if is_landscape else (827, 1169)
        print(f'  <diagram id="{page_id}" name="{name}">')
        print(f'    <mxGraphModel pageWidth="{pw}" pageHeight="{ph}" math="0" shadow="0">')
        print('      <root>')
        print('        <mxCell id="0" />')
        print('        <mxCell id="1" parent="0" />')
        print('        <!-- nodes and edges here -->')
        print('      </root>')
        print('    </mxGraphModel>')
        print(f'  </diagram>')
    print('</mxfile>')


# ─── Legend helper ────────────────────────────────────────────────────────────

def cmd_legend(lowest_y, topology="pipeline"):
    """Output legend position and mxCell XML snippet.

    Args:
        lowest_y: y coordinate of the bottom of the lowest element on the page
        topology: pipeline | microservice | layered (determines which colours to show)
    """
    lowest_y = int(lowest_y)
    topology = topology.lower()

    legend_y = lowest_y + 40
    legend_x = 20
    legend_w = 140
    legend_h = 70

    print(f"legend_x={legend_x}")
    print(f"legend_y={legend_y}")
    print(f"legend_w={legend_w}")
    print(f"legend_h={legend_h}")
    print()

    if topology == "microservice":
        value = (
            '━━ &lt;font color=&quot;#6c8ebf&quot;&gt;HTTP&lt;/font&gt;&lt;br/&gt;'
            '━━━ &lt;font color=&quot;#9673a6&quot;&gt;gRPC&lt;/font&gt;&lt;br/&gt;'
            '┄┄ &lt;font color=&quot;#d79b00&quot;&gt;WebSocket&lt;/font&gt;&lt;br/&gt;'
            '┄┄ &lt;font color=&quot;#82b366&quot;&gt;pub/sub&lt;/font&gt;'
        )
        legend_h = 80
    elif topology == "layered":
        value = (
            '━━ &lt;font color=&quot;#6c8ebf&quot;&gt;config flow&lt;/font&gt;&lt;br/&gt;'
            '━━ &lt;font color=&quot;#82b366&quot;&gt;data flow&lt;/font&gt;&lt;br/&gt;'
            '┄┄ &lt;font color=&quot;#d79b00&quot;&gt;optional&lt;/font&gt;'
        )
        legend_h = 60
    else:  # pipeline
        value = (
            '━━ sequential&lt;br/&gt;'
            '━━ &lt;font color=&quot;#82b366&quot;&gt;pass&lt;/font&gt;&lt;br/&gt;'
            '━━ &lt;font color=&quot;#b85450&quot;&gt;fail&lt;/font&gt;'
        )
        legend_h = 60

    print("# Paste this mxCell into your drawio XML:")
    print(f'<mxCell id="legend" value="{value}"')
    print(f'  style="text;html=1;align=left;verticalAlign=top;fontSize=10;fillColor=none;strokeColor=none;"')
    print(f'  vertex="1" parent="1">')
    print(f'  <mxGeometry x="{legend_x}" y="{legend_y}" width="{legend_w}" height="{legend_h}" as="geometry" />')
    print(f'</mxCell>')


# ─── Step height helper ──────────────────────────────────────────────────────

def cmd_step_height(*label_parts):
    """Compute step box height from a label containing <br/> line breaks.

    Accepts the label as one or more arguments (joined with spaces).
    Counts <br/> occurrences to determine line count, then applies formula:
      h = max(36, 22 + n_lines * 18)
    """
    label = " ".join(label_parts)
    if not label:
        print("usage: layout.py step-height \"Line 1<br/>Line 2<br/>Line 3\"", file=sys.stderr)
        sys.exit(1)

    n_breaks = label.lower().count("<br/>") + label.lower().count("<br>")
    n_lines = n_breaks + 1
    h = max(36, 22 + n_lines * 18)

    print(f"n_lines={n_lines}")
    print(f"height={h}")
    print(f"# Formula: max(36, 22 + {n_lines} × 18) = {h}")


# ─── Text width helper ───────────────────────────────────────────────────────

def cmd_text_width(*label_parts):
    """Compute minimum box width to fit a label without overflow.

    Parses <br/> to find the longest line, then computes:
      min_width = longest_line_chars * 5.5 + 16 (padding)

    Also outputs the max chars allowed for common box widths.
    """
    label = " ".join(label_parts)
    if not label:
        print("usage: layout.py text-width \"Line 1<br/>Second longer line\"", file=sys.stderr)
        sys.exit(1)

    # Split on <br/> and <br>
    import re
    text = re.sub(r"<br\s*/?>", "\n", label, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)  # strip HTML tags
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    if not lines:
        print("min_width=50")
        return

    longest = max(len(l) for l in lines)
    min_width = int(longest * 5.5 + 16)

    print(f"longest_line={longest} chars")
    print(f"min_width={min_width}px")
    print(f"# Common widths: 200px=max 33 chars, 240px=max 40 chars, 280px=max 48 chars")
    if longest > 40:
        print(f"# WARNING: {longest} chars needs {min_width}px — consider abbreviating to ≤40 chars")


# ─── Shared layer helper ─────────────────────────────────────────────────────

def cmd_shared_layer(n_items, container_y=None, page_w=None):
    """Compute full-width dashed container with N evenly-spaced child boxes inside.

    For "environment" or "shared domain" bands that span the full page width
    with individual service/component boxes inside.

    Args:
        n_items: number of child boxes inside the container
        container_y: y position of the container (default: 800, near bottom)
        page_w: page width (default: 827)
    """
    n_items = int(n_items)
    container_y = int(container_y) if container_y else 800
    page_w = int(page_w) if page_w else 827

    if n_items < 1 or n_items > 12:
        print("usage: layout.py shared-layer <n_items> [container_y] [page_w]\n"
              "  n_items must be 1-12", file=sys.stderr)
        sys.exit(1)

    margin_x = 30
    container_x = margin_x
    container_w = page_w - 2 * margin_x
    container_h = 100
    header_h = 30
    item_h = 50
    item_gap = 20
    item_padding = 20

    # Child items
    available_w = container_w - 2 * item_padding
    item_w = min(160, (available_w - (n_items - 1) * item_gap) // n_items)
    items_total_w = n_items * item_w + (n_items - 1) * item_gap
    first_item_x = (container_w - items_total_w) // 2

    container_h = header_h + 10 + item_h + 15  # header + gap + items + bottom

    print(f"# Full-width dashed container (shared layer / environment band)")
    print(f"container: x={container_x} y={container_y} w={container_w} h={container_h}")
    print(f'style="rounded=1;fillColor=#fef5f5;strokeColor=#b85450;strokeWidth=2;'
          f'dashed=1;dashPattern=8 4;verticalAlign=top;fontStyle=1;fontSize=12;'
          f'swimlane;startSize={header_h};html=1;"')
    print()
    for i in range(n_items):
        ix = first_item_x + i * (item_w + item_gap)
        iy = header_h + 10
        print(f"  child[{i}]: x={ix} y={iy} w={item_w} h={item_h}  (relative to container)")

    print()
    print(f"container_h={container_h}")


# ─── Scaffold helper ─────────────────────────────────────────────────────────

def cmd_scaffold(topology, n_stages="3"):
    """Output a complete positioned drawio XML with swimlanes and stub edges.

    Args:
        topology: pipeline | microservice | layered
        n_stages: number of stages/services/layers (default 3)
    """
    topology = topology.lower()
    n = int(n_stages)

    if topology not in ("pipeline", "microservice", "layered"):
        print("usage: layout.py scaffold <pipeline|microservice|layered> [n_stages]",
              file=sys.stderr)
        sys.exit(1)

    if topology == "pipeline":
        _scaffold_pipeline(n)
    elif topology == "microservice":
        _scaffold_microservice(n)
    elif topology == "layered":
        _scaffold_layered(n)


def _scaffold_pipeline(n):
    """Generate a complete pipeline drawio with N swimlanes."""
    # Compute layout
    sw_w = min(316, math.floor((_PAGE_W - _MARGIN - (n - 1) * _SW_GAP) / n))
    step_w = sw_w - 36
    total_w = n * sw_w + (n - 1) * _SW_GAP
    first_x = math.floor((_PAGE_W - total_w) / 2)

    # Input row
    input_y = 30
    input_h = 40
    # Swimlane row
    sl_y = input_y + input_h + 60
    sl_start_size = 30
    # Each swimlane gets 3 stub steps (2 lines each)
    step_h = 58  # max(36, 22 + 2*18)
    n_steps = 3
    sl_h = sl_start_size + 26 + n_steps * (step_h + _STEP_GAP) - _STEP_GAP + 20

    print('<?xml version="1.0" encoding="UTF-8"?>')
    print('<mxfile host="ac.draw.io">')
    print('  <diagram id="overview" name="Pipeline Overview">')
    print(f'    <mxGraphModel pageWidth="827" pageHeight="1169" math="0" shadow="0">')
    print('      <root>')
    print('        <mxCell id="0" />')
    print('        <mxCell id="1" parent="0" />')

    # Input nodes
    inp_total_w = n * _INPUT_W + (n - 1) * _INPUT_GAP
    inp_first_x = math.floor((_PAGE_W - inp_total_w) / 2)
    for i in range(n):
        ix = inp_first_x + i * (_INPUT_W + _INPUT_GAP)
        print(f'        <mxCell id="input-{i}" value="Input {i+1}" '
              f'style="rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;html=1;" '
              f'vertex="1" parent="1">')
        print(f'          <mxGeometry x="{ix}" y="{input_y}" width="{_INPUT_W}" height="{input_h}" as="geometry" />')
        print(f'        </mxCell>')

    # Swimlanes with steps
    for i in range(n):
        sl_x = first_x + i * (sw_w + _SW_GAP)
        sl_id = f"sl-{i}"
        print(f'        <mxCell id="{sl_id}" value="Stage {i+1}" '
              f'style="swimlane;startSize={sl_start_size};fillColor=#ffe6cc;strokeColor=#d79b00;'
              f'fontStyle=1;fontSize=12;html=1;" vertex="1" parent="1">')
        print(f'          <mxGeometry x="{sl_x}" y="{sl_y}" width="{sw_w}" height="{sl_h}" as="geometry" />')
        print(f'        </mxCell>')

        # Steps inside
        step_y = sl_start_size + 26
        for j in range(n_steps):
            step_id = f"step-{i}-{j}"
            print(f'        <mxCell id="{step_id}" value="Step {j+1}&lt;br/&gt;detail" '
                  f'style="rounded=1;fillColor=#ffffff;strokeColor=#d79b00;html=1;" '
                  f'vertex="1" parent="{sl_id}">')
            print(f'          <mxGeometry x="18" y="{step_y}" width="{step_w}" height="{step_h}" as="geometry" />')
            print(f'        </mxCell>')
            step_y += step_h + _STEP_GAP

    # Edges: input → swimlane
    for i in range(n):
        print(f'        <mxCell id="e-in-{i}" edge="1" source="input-{i}" target="sl-{i}" '
              f'style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeWidth=2;'
              f'exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" '
              f'parent="1">')
        print(f'          <mxGeometry relative="1" as="geometry" />')
        print(f'        </mxCell>')

    print('      </root>')
    print('    </mxGraphModel>')
    print('  </diagram>')
    print('</mxfile>')


def _scaffold_microservice(n):
    """Generate a microservice scaffold with N services in a 2-layer layout."""
    page_w, page_h = 1169, 827
    margin = 60
    container_w = 180
    container_h = 120
    h_gap = (page_w - 2 * margin - n * container_w) // max(1, n - 1) if n > 1 else 0

    print('<?xml version="1.0" encoding="UTF-8"?>')
    print('<mxfile host="ac.draw.io">')
    print('  <diagram id="service-map" name="Service Map">')
    print(f'    <mxGraphModel pageWidth="{page_w}" pageHeight="{page_h}" math="0" shadow="0">')
    print('      <root>')
    print('        <mxCell id="0" />')
    print('        <mxCell id="1" parent="0" />')

    # Gateway layer
    gw_y = margin
    gw_x = (page_w - container_w) // 2
    print(f'        <mxCell id="gateway" value="API Gateway" '
          f'style="rounded=1;fillColor=#e1d5e7;strokeColor=#9673a6;html=1;'
          f'verticalAlign=top;fontStyle=1;fontSize=12;swimlane;startSize=30;" '
          f'vertex="1" parent="1">')
    print(f'          <mxGeometry x="{gw_x}" y="{gw_y}" width="{container_w}" height="{container_h}" as="geometry" />')
    print(f'        </mxCell>')

    # Service layer
    svc_y = gw_y + container_h + 100
    svc_total_w = n * container_w + (n - 1) * max(60, h_gap)
    svc_first_x = (page_w - svc_total_w) // 2

    for i in range(n):
        sx = svc_first_x + i * (container_w + max(60, h_gap))
        svc_id = f"svc-{i}"
        print(f'        <mxCell id="{svc_id}" value="Service {i+1}" '
              f'style="rounded=1;fillColor=#e1d5e7;strokeColor=#9673a6;html=1;'
              f'verticalAlign=top;fontStyle=1;fontSize=12;swimlane;startSize=30;" '
              f'vertex="1" parent="1">')
        print(f'          <mxGeometry x="{sx}" y="{svc_y}" width="{container_w}" height="{container_h}" as="geometry" />')
        print(f'        </mxCell>')

        # Edge from gateway
        print(f'        <mxCell id="e-gw-{i}" edge="1" source="gateway" target="{svc_id}" '
              f'style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#6c8ebf;strokeWidth=2;'
              f'exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" '
              f'value="REST" parent="1">')
        print(f'          <mxGeometry relative="1" as="geometry" />')
        print(f'        </mxCell>')

    # Infrastructure layer
    infra_y = svc_y + container_h + 100
    infra_x = (page_w - container_w) // 2
    print(f'        <mxCell id="db" value="PostgreSQL" '
          f'style="shape=cylinder3;fillColor=#dae8fc;strokeColor=#6c8ebf;html=1;'
          f'boundedLbl=1;backgroundOutline=1;size=10;fontSize=12;" '
          f'vertex="1" parent="1">')
    print(f'          <mxGeometry x="{infra_x}" y="{infra_y}" width="{container_w}" height="{container_h}" as="geometry" />')
    print(f'        </mxCell>')

    print('      </root>')
    print('    </mxGraphModel>')
    print('  </diagram>')
    print('</mxfile>')


def _scaffold_layered(n):
    """Generate a layered architecture scaffold with N layers."""
    page_w = 827
    margin_x = 30
    margin_y = 30
    band_w = page_w - 2 * margin_x
    layer_gap = 30
    layer_h = 90

    roles = ["Config", "Processing", "Environment"]
    palette_keys = ["config", "generator", "environment"]

    print('<?xml version="1.0" encoding="UTF-8"?>')
    print('<mxfile host="ac.draw.io">')
    print('  <diagram id="arch" name="Architecture Overview">')
    print(f'    <mxGraphModel pageWidth="{page_w}" pageHeight="1169" math="0" shadow="0">')
    print('      <root>')
    print('        <mxCell id="0" />')
    print('        <mxCell id="1" parent="0" />')

    y = margin_y
    for i in range(min(n, len(roles))):
        role = roles[i] if i < len(roles) else f"Layer {i+1}"
        pk = palette_keys[i] if i < len(palette_keys) else "neutral"
        p = _PALETTE.get(pk, _PALETTE["neutral"])

        layer_id = f"layer-{i}"
        print(f'        <mxCell id="{layer_id}" value="{role}" '
              f'style="rounded=1;fillColor={p["fill"]};strokeColor={p["stroke"]};html=1;'
              f'verticalAlign=top;fontStyle=1;fontSize=12;swimlane;startSize=30;" '
              f'vertex="1" parent="1">')
        print(f'          <mxGeometry x="{margin_x}" y="{y}" width="{band_w}" height="{layer_h}" as="geometry" />')
        print(f'        </mxCell>')

        # 2 stub items inside
        item_w = 160
        item_h = 40
        item_y = 35
        ix1 = (band_w - 2 * item_w - 40) // 2
        ix2 = ix1 + item_w + 40
        print(f'        <mxCell id="item-{i}-0" value="Component A" '
              f'style="rounded=1;fillColor=#ffffff;strokeColor={p["stroke"]};html=1;" '
              f'vertex="1" parent="{layer_id}">')
        print(f'          <mxGeometry x="{ix1}" y="{item_y}" width="{item_w}" height="{item_h}" as="geometry" />')
        print(f'        </mxCell>')
        print(f'        <mxCell id="item-{i}-1" value="Component B" '
              f'style="rounded=1;fillColor=#ffffff;strokeColor={p["stroke"]};html=1;" '
              f'vertex="1" parent="{layer_id}">')
        print(f'          <mxGeometry x="{ix2}" y="{item_y}" width="{item_w}" height="{item_h}" as="geometry" />')
        print(f'        </mxCell>')

        y += layer_h + layer_gap

    # Edges between layers
    for i in range(min(n, len(roles)) - 1):
        print(f'        <mxCell id="e-layer-{i}" edge="1" source="layer-{i}" target="layer-{i+1}" '
              f'style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeWidth=2;'
              f'exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" '
              f'parent="1">')
        print(f'          <mxGeometry relative="1" as="geometry" />')
        print(f'        </mxCell>')

    print('      </root>')
    print('    </mxGraphModel>')
    print('  </diagram>')
    print('</mxfile>')


# ─── Page size helper ─────────────────────────────────────────────────────────

def cmd_page_size(lowest_y, rightmost_x=None):
    """Compute custom pageWidth and pageHeight from content bounds.

    Args:
        lowest_y: y coordinate of the bottom of the lowest element (element_y + element_h)
        rightmost_x: x coordinate of the right edge of the rightmost element (optional)
    """
    lowest_y = int(lowest_y)
    rightmost_x = int(rightmost_x) if rightmost_x else 797  # default = 767 band + 30 margin

    margin = 40
    legend_h = 80  # room for legend below content

    page_h = lowest_y + legend_h + margin
    page_w = max(rightmost_x + margin, 600)  # minimum 600px wide

    # Round up to nearest 10 for clean numbers
    page_h = ((page_h + 9) // 10) * 10
    page_w = ((page_w + 9) // 10) * 10

    print(f"page_w={page_w}")
    print(f"page_h={page_h}")
    print(f"# Set in <mxGraphModel pageWidth=\"{page_w}\" pageHeight=\"{page_h}\" ...>")


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
        "palette":          lambda: cmd_palette(*args),
        "layers":           lambda: cmd_layers(*args),
        "boilerplate":      lambda: cmd_boilerplate(*args),
        "legend":           lambda: cmd_legend(*args),
        "step-height":      lambda: cmd_step_height(*args),
        "text-width":       lambda: cmd_text_width(*args),
        "shared-layer":     lambda: cmd_shared_layer(*args),
        "scaffold":         lambda: cmd_scaffold(*args),
        "page-size":        lambda: cmd_page_size(*args),
    }
    fn = dispatch.get(cmd)
    if fn is None:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
    fn()


if __name__ == "__main__":
    main()
