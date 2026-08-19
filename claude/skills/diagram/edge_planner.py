#!/usr/bin/env python3
"""Edge planner with obstacle-aware pathfinding.

Takes a JSON description of nodes and edges, computes waypoints that avoid all
boxes, and outputs edge definitions with explicit waypoint arrays.

Usage:
  edge_planner.py <input.json>

Input JSON format:
{
  "page_w": 1169,
  "page_h": 1140,
  "nodes": {
    "node-id": {"x": 100, "y": 200, "w": 200, "h": 140},
    "child-id": {"x": 18, "y": 45, "w": 160, "h": 50, "parent": "node-id"},
    ...
  },
  "edges": [
    {"id": "e1", "source": "node-a", "target": "node-b", "label": "REST /api", "protocol": "http"},
    ...
  ]
}

Output JSON format:
{
  "edges": [
    {
      "id": "e1",
      "source": "node-a",
      "target": "node-b",
      "exitX": 0.5, "exitY": 1.0,
      "entryX": 0.5, "entryY": 0.0,
      "waypoints": [{"x": 300, "y": 450}, {"x": 500, "y": 450}],
      "label": "REST /api",
      "protocol": "http"
    },
    ...
  ],
  "warnings": [],
  "legend": {"http": "#6c8ebf", "grpc": "#9673a6", "websocket": "#d79b00", "pubsub": "#82b366", "database": "#6c8ebf"}
}

Protocols: http, grpc, websocket, pubsub, database, sequential, pass, fail
"""

import json
import math
import sys
from collections import defaultdict


# Inflate boxes by this margin when checking edge paths
BOX_MARGIN = 15


def inflate_box(node, margin=BOX_MARGIN):
    """Return inflated bounding box (x, y, w, h) with margin."""
    return (
        node["x"] - margin,
        node["y"] - margin,
        node["w"] + 2 * margin,
        node["h"] + 2 * margin,
    )


def box_contains_point(bx, by, bw, bh, px, py):
    """Check if point (px, py) is inside box (bx, by, bw, bh)."""
    return bx < px < bx + bw and by < py < by + bh


def segment_crosses_box(x1, y1, x2, y2, bx, by, bw, bh):
    """Check if an orthogonal segment (horizontal or vertical) passes through a box interior."""
    if y1 == y2:  # Horizontal segment
        seg_y = y1
        seg_x_min = min(x1, x2)
        seg_x_max = max(x1, x2)
        # Segment crosses box if it's within the box's y-range and x-ranges overlap
        if by < seg_y < by + bh:
            if seg_x_min < bx + bw and seg_x_max > bx:
                return True
    elif x1 == x2:  # Vertical segment
        seg_x = x1
        seg_y_min = min(y1, y2)
        seg_y_max = max(y1, y2)
        if bx < seg_x < bx + bw:
            if seg_y_min < by + bh and seg_y_max > by:
                return True
    return False


def compute_exit_point(node, direction, slot=0.5):
    """Compute absolute exit point coordinates."""
    x, y, w, h = node["x"], node["y"], node["w"], node["h"]
    if direction == "bottom":
        return (x + w * slot, y + h)
    elif direction == "top":
        return (x + w * slot, y)
    elif direction == "right":
        return (x + w, y + h * slot)
    elif direction == "left":
        return (x, y + h * slot)


def compute_entry_point(node, direction, slot=0.5):
    """Compute absolute entry point coordinates."""
    x, y, w, h = node["x"], node["y"], node["w"], node["h"]
    if direction == "top":
        return (x + w * slot, y)
    elif direction == "bottom":
        return (x + w * slot, y + h)
    elif direction == "left":
        return (x, y + h * slot)
    elif direction == "right":
        return (x + w, y + h * slot)


def determine_best_sides(src_node, tgt_node):
    """Determine which sides of source and target to use for the edge."""
    src_cx = src_node["x"] + src_node["w"] / 2
    src_cy = src_node["y"] + src_node["h"] / 2
    tgt_cx = tgt_node["x"] + tgt_node["w"] / 2
    tgt_cy = tgt_node["y"] + tgt_node["h"] / 2

    dx = tgt_cx - src_cx
    dy = tgt_cy - src_cy

    if abs(dy) > abs(dx):
        if dy > 0:
            return "bottom", "top"
        else:
            return "top", "bottom"
    else:
        if dx > 0:
            return "right", "left"
        else:
            return "left", "right"


def route_edge_around_obstacles(start_x, start_y, end_x, end_y, obstacles, src_id, tgt_id):
    """
    Compute orthogonal waypoints from start to end that avoid all obstacle boxes.
    Uses a simple L-shaped or Z-shaped routing strategy.
    
    Returns list of waypoints [(x,y), ...] between start and end (exclusive of start/end).
    """
    # Check if a direct L-route works (one bend)
    # Try horizontal-then-vertical
    mid_point_hv = (end_x, start_y)  # go horizontal first, then vertical
    mid_point_vh = (start_x, end_y)  # go vertical first, then horizontal

    # Check horizontal-then-vertical route
    hv_clear = True
    for obs_id, obs in obstacles.items():
        if obs_id == src_id or obs_id == tgt_id:
            continue
        bx, by, bw, bh = inflate_box(obs)
        # Horizontal segment: start → mid_hv
        if segment_crosses_box(start_x, start_y, end_x, start_y, bx, by, bw, bh):
            hv_clear = False
            break
        # Vertical segment: mid_hv → end
        if segment_crosses_box(end_x, start_y, end_x, end_y, bx, by, bw, bh):
            hv_clear = False
            break

    if hv_clear:
        # Only add waypoint if it's not colinear (i.e., not a straight line)
        if start_x != end_x and start_y != end_y:
            return [{"x": int(end_x), "y": int(start_y)}]
        return []

    # Check vertical-then-horizontal route
    vh_clear = True
    for obs_id, obs in obstacles.items():
        if obs_id == src_id or obs_id == tgt_id:
            continue
        bx, by, bw, bh = inflate_box(obs)
        # Vertical segment: start → mid_vh
        if segment_crosses_box(start_x, start_y, start_x, end_y, bx, by, bw, bh):
            vh_clear = False
            break
        # Horizontal segment: mid_vh → end
        if segment_crosses_box(start_x, end_y, end_x, end_y, bx, by, bw, bh):
            vh_clear = False
            break

    if vh_clear:
        if start_x != end_x and start_y != end_y:
            return [{"x": int(start_x), "y": int(end_y)}]
        return []

    # Neither L-route works. Try Z-route (two bends) via margins.
    # Find a clear horizontal band between start_y and end_y
    page_margin_left = 30
    page_margin_right = 30  # will be computed from page_w if available
    
    # Try routing via the left margin
    margin_x = page_margin_left
    left_clear = True
    for obs_id, obs in obstacles.items():
        if obs_id == src_id or obs_id == tgt_id:
            continue
        bx, by, bw, bh = inflate_box(obs)
        # Horizontal: start → left margin
        if segment_crosses_box(start_x, start_y, margin_x, start_y, bx, by, bw, bh):
            left_clear = False
            break
        # Vertical: along left margin
        if segment_crosses_box(margin_x, start_y, margin_x, end_y, bx, by, bw, bh):
            left_clear = False
            break
        # Horizontal: left margin → end
        if segment_crosses_box(margin_x, end_y, end_x, end_y, bx, by, bw, bh):
            left_clear = False
            break

    if left_clear:
        return [
            {"x": int(margin_x), "y": int(start_y)},
            {"x": int(margin_x), "y": int(end_y)},
        ]

    # Try routing via the right margin (use page_w - 30 or estimate)
    # Estimate page right from node positions
    max_right = max(n["x"] + n["w"] for n in obstacles.values()) + 60
    margin_x_right = max_right

    right_clear = True
    for obs_id, obs in obstacles.items():
        if obs_id == src_id or obs_id == tgt_id:
            continue
        bx, by, bw, bh = inflate_box(obs)
        if segment_crosses_box(start_x, start_y, margin_x_right, start_y, bx, by, bw, bh):
            right_clear = False
            break
        if segment_crosses_box(margin_x_right, start_y, margin_x_right, end_y, bx, by, bw, bh):
            right_clear = False
            break
        if segment_crosses_box(margin_x_right, end_y, end_x, end_y, bx, by, bw, bh):
            right_clear = False
            break

    if right_clear:
        return [
            {"x": int(margin_x_right), "y": int(start_y)},
            {"x": int(margin_x_right), "y": int(end_y)},
        ]

    # Try a mid-y routing band (halfway between start and end)
    mid_y = int((start_y + end_y) / 2)
    # Find a y that's clear of all boxes
    for offset in range(0, 200, 20):
        for candidate_y in [mid_y + offset, mid_y - offset]:
            clear = True
            for obs_id, obs in obstacles.items():
                if obs_id == src_id or obs_id == tgt_id:
                    continue
                bx, by, bw, bh = inflate_box(obs)
                # Check horizontal at candidate_y from start_x to end_x
                if segment_crosses_box(start_x, candidate_y, end_x, candidate_y, bx, by, bw, bh):
                    clear = False
                    break
                # Check vertical from start to candidate_y
                if segment_crosses_box(start_x, start_y, start_x, candidate_y, bx, by, bw, bh):
                    clear = False
                    break
                # Check vertical from candidate_y to end
                if segment_crosses_box(end_x, candidate_y, end_x, end_y, bx, by, bw, bh):
                    clear = False
                    break
            if clear:
                return [
                    {"x": int(start_x), "y": candidate_y},
                    {"x": int(end_x), "y": candidate_y},
                ]

    # Fallback: just use L-route (horizontal-first) even if it crosses something
    # The validator will flag it
    if start_x != end_x and start_y != end_y:
        return [{"x": int(end_x), "y": int(start_y)}]
    return []


def spread_slots(n):
    """Generate N evenly-spaced fractions in [0.2, 0.8]."""
    if n == 1:
        return [0.5]
    elif n == 2:
        return [0.3, 0.7]
    elif n == 3:
        return [0.2, 0.5, 0.8]
    else:
        return [0.15 + (0.7 * i / (n - 1)) for i in range(n)]


def resolve_hierarchy(nodes):
    """Resolve hierarchical node positions to absolute coordinates.

    If a node has a "parent" field, its x/y are relative to that parent.
    This function computes absolute x/y by walking up the parent chain.
    Nodes without a parent are already absolute.

    Returns a new dict with the same keys but absolute x/y values.
    """
    resolved = {}

    def resolve_node(node_id):
        if node_id in resolved:
            return resolved[node_id]
        node = nodes[node_id]
        parent_id = node.get("parent")
        if parent_id and parent_id in nodes:
            parent = resolve_node(parent_id)
            abs_x = node["x"] + parent["x"]
            abs_y = node["y"] + parent["y"]
        else:
            abs_x = node["x"]
            abs_y = node["y"]
        resolved[node_id] = {"x": abs_x, "y": abs_y, "w": node["w"], "h": node["h"]}
        return resolved[node_id]

    for node_id in nodes:
        resolve_node(node_id)

    return resolved


def plan_edges(data):
    """Main planning function."""
    nodes = data.get("nodes", {})
    edges = data.get("edges", [])
    page_w = data.get("page_w", 1169)
    page_h = data.get("page_h", 1140)

    # Resolve hierarchical positions: if a node has "parent", compute absolute x/y
    resolved_nodes = resolve_hierarchy(nodes)

    # Group edges by (exit_side, source) for slot spreading
    edges_by_source_side = defaultdict(list)

    # First pass: determine sides for each edge
    edge_sides = {}
    for edge in edges:
        src_id = edge["source"]
        tgt_id = edge["target"]
        if src_id not in resolved_nodes or tgt_id not in resolved_nodes:
            continue
        exit_side, entry_side = determine_best_sides(resolved_nodes[src_id], resolved_nodes[tgt_id])
        edge_sides[edge["id"]] = (exit_side, entry_side)
        edges_by_source_side[(src_id, exit_side)].append(edge["id"])

    # Assign spread slots per source+side group
    edge_exit_slots = {}
    for (src_id, side), edge_ids in edges_by_source_side.items():
        slots = spread_slots(len(edge_ids))
        for i, eid in enumerate(edge_ids):
            edge_exit_slots[eid] = slots[i]

    # Group by target+side for entry slot spreading
    edges_by_target_side = defaultdict(list)
    for edge in edges:
        if edge["id"] not in edge_sides:
            continue
        _, entry_side = edge_sides[edge["id"]]
        edges_by_target_side[(edge["target"], entry_side)].append(edge["id"])

    edge_entry_slots = {}
    for (tgt_id, side), edge_ids in edges_by_target_side.items():
        slots = spread_slots(len(edge_ids))
        for i, eid in enumerate(edge_ids):
            edge_entry_slots[eid] = slots[i]

    # Second pass: compute waypoints with obstacle avoidance
    result = []
    warnings = []
    used_segments = []  # Track used horizontal/vertical segments for overlap detection

    for edge in edges:
        eid = edge["id"]
        src_id = edge["source"]
        tgt_id = edge["target"]

        if eid not in edge_sides:
            warnings.append(f"edge {eid}: source or target not in nodes, skipped")
            continue

        exit_side, entry_side = edge_sides[eid]
        exit_slot = edge_exit_slots.get(eid, 0.5)
        entry_slot = edge_entry_slots.get(eid, 0.5)

        src_node = resolved_nodes[src_id]
        tgt_node = resolved_nodes[tgt_id]

        # Compute absolute start/end points
        start_x, start_y = compute_exit_point(src_node, exit_side, exit_slot)
        end_x, end_y = compute_entry_point(tgt_node, entry_side, entry_slot)

        # Convert exit/entry to fractional for the XML style
        if exit_side == "bottom":
            exitX, exitY = exit_slot, 1.0
        elif exit_side == "top":
            exitX, exitY = exit_slot, 0.0
        elif exit_side == "right":
            exitX, exitY = 1.0, exit_slot
        elif exit_side == "left":
            exitX, exitY = 0.0, exit_slot

        if entry_side == "top":
            entryX, entryY = entry_slot, 0.0
        elif entry_side == "bottom":
            entryX, entryY = entry_slot, 1.0
        elif entry_side == "left":
            entryX, entryY = 0.0, entry_slot
        elif entry_side == "right":
            entryX, entryY = 1.0, entry_slot

        # Route with obstacle avoidance (use resolved positions for all nodes)
        waypoints = route_edge_around_obstacles(
            start_x, start_y, end_x, end_y, resolved_nodes, src_id, tgt_id
        )

        result.append({
            "id": eid,
            "source": src_id,
            "target": tgt_id,
            "exitX": round(exitX, 4),
            "exitY": round(exitY, 4),
            "entryX": round(entryX, 4),
            "entryY": round(entryY, 4),
            "waypoints": waypoints,
            "label": edge.get("label", ""),
            "protocol": edge.get("protocol", "http"),
        })

    if len(result) > 15:
        warnings.append(f"WARNING: {len(result)} edges — consider splitting into multiple pages (max 12 recommended)")

    return {
        "edges": result,
        "warnings": warnings,
        "legend": {
            "http": "#6c8ebf",
            "grpc": "#9673a6",
            "websocket": "#d79b00",
            "pubsub": "#82b366",
            "database": "#6c8ebf",
        },
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    input_path = sys.argv[1]
    with open(input_path) as f:
        data = json.load(f)

    result = plan_edges(data)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
