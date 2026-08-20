#!/usr/bin/env python3
"""Validate a draw.io XML file for layout issues.

Checks:
- Edges passing through boxes (not their source/target)
- Overlapping edge segments (same path, same colour = invisible)
- Edge labels that overlap boxes
- Missing strokeWidth
- Too many edges per page

Usage:
  validate.py <file.drawio>

Exit 0 if clean, exit 1 if issues found.
"""

import sys
import xml.etree.ElementTree as ET
from collections import defaultdict


def parse_style(style_str):
    """Parse a draw.io style string into a dict."""
    result = {}
    if not style_str:
        return result
    for part in style_str.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            result[k] = v
        elif part.strip():
            result[part.strip()] = "1"
    return result


def get_geometry(cell):
    """Extract geometry from an mxCell."""
    geom = cell.find("mxGeometry")
    if geom is None:
        return None
    return {
        "x": float(geom.get("x", 0)),
        "y": float(geom.get("y", 0)),
        "w": float(geom.get("width", 0)),
        "h": float(geom.get("height", 0)),
    }


def get_waypoints(cell):
    """Extract waypoints from an edge's geometry."""
    geom = cell.find("mxGeometry")
    if geom is None:
        return []
    array = geom.find("Array")
    if array is None:
        return []
    points = []
    for pt in array.findall("mxPoint"):
        x = float(pt.get("x", 0))
        y = float(pt.get("y", 0))
        points.append((x, y))
    return points


def compute_edge_path(cell, nodes, parent_offsets):
    """Compute the full path of an edge as a list of (x, y) points."""
    source_id = cell.get("source", "")
    target_id = cell.get("target", "")
    style = parse_style(cell.get("style", ""))
    parent = cell.get("parent", "1")

    # Get offset from parent if edge is inside a container
    offset_x, offset_y = parent_offsets.get(parent, (0, 0))

    # Compute start point from source
    start = None
    if source_id in nodes:
        src = nodes[source_id]
        exit_x = float(style.get("exitX", 0.5))
        exit_y = float(style.get("exitY", 1.0))
        start = (
            src["abs_x"] + src["w"] * exit_x,
            src["abs_y"] + src["h"] * exit_y,
        )

    # Compute end point from target
    end = None
    if target_id in nodes:
        tgt = nodes[target_id]
        entry_x = float(style.get("entryX", 0.5))
        entry_y = float(style.get("entryY", 0.0))
        end = (
            tgt["abs_x"] + tgt["w"] * entry_x,
            tgt["abs_y"] + tgt["h"] * entry_y,
        )

    if not start or not end:
        return []

    # Get waypoints
    waypoints = get_waypoints(cell)
    # Apply parent offset to waypoints
    waypoints = [(x + offset_x, y + offset_y) for x, y in waypoints]

    # Full path
    path = [start] + waypoints + [end]
    return path


def segments_from_path(path):
    """Convert a path into horizontal and vertical segments."""
    segments = []
    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        segments.append((x1, y1, x2, y2))
    return segments


def segment_crosses_box(x1, y1, x2, y2, bx, by, bw, bh):
    """Check if a segment passes through a box interior."""
    # Handle orthogonal segments
    if abs(y1 - y2) < 1:  # Horizontal
        seg_y = y1
        seg_x_min = min(x1, x2)
        seg_x_max = max(x1, x2)
        if by < seg_y < by + bh:
            if seg_x_min < bx + bw and seg_x_max > bx:
                # Check it's not just touching the border
                overlap_x = min(seg_x_max, bx + bw) - max(seg_x_min, bx)
                if overlap_x > 5:  # More than a border touch
                    return True
    elif abs(x1 - x2) < 1:  # Vertical
        seg_x = x1
        seg_y_min = min(y1, y2)
        seg_y_max = max(y1, y2)
        if bx < seg_x < bx + bw:
            if seg_y_min < by + bh and seg_y_max > by:
                overlap_y = min(seg_y_max, by + bh) - max(seg_y_min, by)
                if overlap_y > 5:
                    return True
    else:
        # Diagonal segment — check if it passes through box
        # Simple bounding box intersection check
        seg_x_min = min(x1, x2)
        seg_x_max = max(x1, x2)
        seg_y_min = min(y1, y2)
        seg_y_max = max(y1, y2)
        if seg_x_min < bx + bw and seg_x_max > bx and seg_y_min < by + bh and seg_y_max > by:
            return True
    return False


def segments_overlap(seg1, seg2):
    """Check if two segments share the same path (not just cross)."""
    x1a, y1a, x2a, y2a = seg1
    x1b, y1b, x2b, y2b = seg2

    # Both horizontal at same y
    if abs(y1a - y2a) < 1 and abs(y1b - y2b) < 1 and abs(y1a - y1b) < 3:
        # Same y, check x overlap
        a_min, a_max = min(x1a, x2a), max(x1a, x2a)
        b_min, b_max = min(x1b, x2b), max(x1b, x2b)
        overlap = min(a_max, b_max) - max(a_min, b_min)
        if overlap > 10:  # More than 10px shared
            return True

    # Both vertical at same x
    if abs(x1a - x2a) < 1 and abs(x1b - x2b) < 1 and abs(x1a - x1b) < 3:
        a_min, a_max = min(y1a, y2a), max(y1a, y2a)
        b_min, b_max = min(y1b, y2b), max(y1b, y2b)
        overlap = min(a_max, b_max) - max(a_min, b_min)
        if overlap > 10:
            return True

    return False


def validate_file(filepath):
    issues = []

    try:
        tree = ET.parse(filepath)
    except ET.ParseError as e:
        return [f"XML PARSE ERROR: {e}"]

    root = tree.getroot()
    diagrams = root.findall("diagram")

    if not diagrams:
        return ["NO DIAGRAMS found"]

    all_ids = set()
    reserved = {"0", "1"}

    for diagram in diagrams:
        page_name = diagram.get("name", diagram.get("id", "unknown"))
        model = diagram.find("mxGraphModel")
        if model is None:
            issues.append(f"[{page_name}] Missing mxGraphModel")
            continue

        root_elem = model.find("root")
        if root_elem is None:
            issues.append(f"[{page_name}] Missing root element")
            continue

        cells = root_elem.findall("mxCell")

        # Build node map with absolute positions
        nodes = {}  # id -> {abs_x, abs_y, w, h}
        parent_offsets = {"1": (0, 0)}  # parent_id -> (offset_x, offset_y)

        # First pass: find all vertices
        for cell in cells:
            if cell.get("vertex") != "1":
                continue
            cell_id = cell.get("id", "")
            parent = cell.get("parent", "1")
            geom = get_geometry(cell)
            if not geom:
                continue

            # Check duplicate IDs
            if cell_id and cell_id not in reserved:
                if cell_id in all_ids:
                    issues.append(f"[{page_name}] DUPLICATE ID: '{cell_id}'")
                all_ids.add(cell_id)

            # Compute absolute position
            off_x, off_y = parent_offsets.get(parent, (0, 0))
            abs_x = geom["x"] + off_x
            abs_y = geom["y"] + off_y

            nodes[cell_id] = {
                "abs_x": abs_x,
                "abs_y": abs_y,
                "w": geom["w"],
                "h": geom["h"],
                "parent": parent,
            }

            # This node can be a parent for children
            parent_offsets[cell_id] = (abs_x, abs_y)

        # Second pass: check edges
        edge_paths = []  # (edge_id, path, colour)
        edge_count = 0

        for cell in cells:
            if cell.get("edge") != "1":
                continue
            edge_count += 1
            cell_id = cell.get("id", "")
            source_id = cell.get("source", "")
            target_id = cell.get("target", "")
            style = parse_style(cell.get("style", ""))
            colour = style.get("strokeColor", "#000000")

            # Check strokeWidth
            sw = style.get("strokeWidth", "1")
            try:
                if int(sw) < 2 and cell.get("parent", "1") == "1":
                    issues.append(
                        f"[{page_name}] THIN EDGE: '{cell_id}' strokeWidth={sw}"
                    )
            except ValueError:
                pass

            # Compute path
            path = compute_edge_path(cell, nodes, parent_offsets)
            if not path:
                continue

            edge_paths.append((cell_id, path, colour, source_id, target_id))

            # Check each segment against all boxes (except source and target)
            segments = segments_from_path(path)
            for seg in segments:
                x1, y1, x2, y2 = seg
                for node_id, node in nodes.items():
                    if node_id == source_id or node_id == target_id:
                        continue
                    # Skip if this node is a parent/child of source/target
                    if node.get("parent") == source_id or node.get("parent") == target_id:
                        continue
                    if nodes.get(source_id, {}).get("parent") == node_id:
                        continue
                    if nodes.get(target_id, {}).get("parent") == node_id:
                        continue

                    if segment_crosses_box(x1, y1, x2, y2,
                                           node["abs_x"], node["abs_y"],
                                           node["w"], node["h"]):
                        # Suppress for layered background bands: full-width swimlanes
                        # that are NOT the source or target are likely background bands.
                        node_style = parse_style(
                            next((c.get("style", "") for c in cells if c.get("id") == node_id), "")
                        )
                        is_background_band = (
                            "swimlane" in node_style
                            and node["w"] > 500  # full-width (>500px = likely a band)
                        )
                        if not is_background_band:
                            issues.append(
                                f"[{page_name}] BOX CROSSING: edge '{cell_id}' "
                                f"passes through '{node_id}'"
                            )
                        break  # One violation per edge is enough

        # Check for overlapping segments between different edges
        for i in range(len(edge_paths)):
            for j in range(i + 1, len(edge_paths)):
                eid_a, path_a, colour_a, _, _ = edge_paths[i]
                eid_b, path_b, colour_b, _, _ = edge_paths[j]

                # Only flag overlap if same colour (different colours are distinguishable)
                if colour_a != colour_b:
                    continue

                segs_a = segments_from_path(path_a)
                segs_b = segments_from_path(path_b)

                for sa in segs_a:
                    for sb in segs_b:
                        if segments_overlap(sa, sb):
                            issues.append(
                                f"[{page_name}] OVERLAP: edges '{eid_a}' and "
                                f"'{eid_b}' share a segment (colour={colour_a})"
                            )
                            break
                    else:
                        continue
                    break

        # Edge count check — different limits for pipeline (portrait) vs service-map (landscape)
        page_w_str = model.get("pageWidth", "827")
        is_landscape = int(page_w_str) > 900  # Service maps are landscape

        # Check for oversized swimlanes (height much larger than content)
        for cell in cells:
            if cell.get("vertex") != "1":
                continue
            style = parse_style(cell.get("style", ""))
            if "swimlane" not in style:
                continue
            cell_id = cell.get("id", "")
            geom = get_geometry(cell)
            if not geom or geom["h"] == 0:
                continue
            # Find the lowest child element
            max_child_bottom = 0
            for child in cells:
                if child.get("parent") == cell_id and child.get("vertex") == "1":
                    child_geom = get_geometry(child)
                    if child_geom:
                        child_bottom = child_geom["y"] + child_geom["h"]
                        max_child_bottom = max(max_child_bottom, child_bottom)
            if max_child_bottom > 0:
                expected_h = max_child_bottom + 20  # 20px bottom padding
                actual_h = geom["h"]
                if actual_h > expected_h + 60:  # More than 60px of dead space
                    issues.append(
                        f"[{page_name}] OVERSIZED SWIMLANE: '{cell_id}' "
                        f"height={int(actual_h)} but content ends at y={int(max_child_bottom)} "
                        f"(expected ~{int(expected_h)})"
                    )

        if is_landscape:
            # Service map: strict limit
            if edge_count > 15:
                issues.append(f"[{page_name}] TOO MANY EDGES: {edge_count} (service map max: 12)")
            elif edge_count > 12:
                issues.append(f"[{page_name}] DENSE SERVICE MAP: {edge_count} edges (max 12 recommended)")
        else:
            # Pipeline: more permissive (mostly vertical edges)
            if edge_count > 25:
                issues.append(f"[{page_name}] TOO MANY EDGES: {edge_count} (pipeline max: 25)")
            elif edge_count > 20:
                issues.append(f"[{page_name}] DENSE PIPELINE: {edge_count} edges (max 20 recommended)")

        # Check for very short cross-service edges with labels (indicates nodes placed too close)
        for i_ep, (eid, path, colour, src_id, tgt_id) in enumerate(edge_paths):
            if len(path) >= 2:
                start = path[0]
                end = path[-1]
                distance = ((end[0] - start[0])**2 + (end[1] - start[1])**2) ** 0.5
                # Only flag if this is a cross-service edge (parent="1") with a label
                # Find the original cell to check parent and value
                for cell in cells:
                    if cell.get("id") == eid:
                        parent = cell.get("parent", "1")
                        value = cell.get("value", "")
                        if distance < 30 and parent == "1" and value:
                            issues.append(
                                f"[{page_name}] SHORT EDGE: '{eid}' ({src_id}→{tgt_id}) "
                                f"distance={int(distance)}px — nodes too close, label will be unreadable"
                            )
                        break

        # ─── Header clearance check ─────────────────────────────────────
        # First child inside a swimlane must be at y >= startSize + 20
        # Only applies to swimlanes that ARE targets of edges (arrows enter them)
        edge_targets = set()
        for cell in cells:
            if cell.get("edge") == "1":
                tgt = cell.get("target", "")
                if tgt:
                    edge_targets.add(tgt)

        for cell in cells:
            if cell.get("vertex") != "1":
                continue
            style = parse_style(cell.get("style", ""))
            if "swimlane" not in style:
                continue
            parent_id = cell.get("id", "")
            # Only check if this swimlane receives incoming edges
            if parent_id not in edge_targets:
                continue
            start_size = int(style.get("startSize", "30"))
            # Find first child by y-position
            first_child_y = None
            for child in cells:
                if child.get("parent") == parent_id and child.get("vertex") == "1":
                    child_geom = get_geometry(child)
                    if child_geom and child_geom["h"] > 0:
                        if first_child_y is None or child_geom["y"] < first_child_y:
                            first_child_y = child_geom["y"]
            if first_child_y is not None and first_child_y < start_size + 20:
                issues.append(
                    f"[{page_name}] HEADER CLEARANCE: '{parent_id}' first child at y={int(first_child_y)} "
                    f"but startSize={start_size} — need y≥{start_size + 26} for arrow visibility"
                )

        # ─── Band overlap check (layered topology) ────────────────────────
        # Root-level items positioned inside a band's header zone
        # (common issue: item y < band_y + startSize)
        band_headers = []  # (band_id, band_y, header_bottom, band_x, band_right)
        for cell in cells:
            if cell.get("vertex") != "1":
                continue
            style = parse_style(cell.get("style", ""))
            if "swimlane" not in style:
                continue
            if cell.get("parent", "1") != "1":
                continue  # only root-level bands
            geom = get_geometry(cell)
            if not geom or geom["w"] < 500:
                continue  # only full-width bands
            ss = int(style.get("startSize", "28"))
            band_headers.append((
                cell.get("id", ""),
                geom["y"],
                geom["y"] + ss,
                geom["x"],
                geom["x"] + geom["w"]
            ))

        for cell in cells:
            if cell.get("vertex") != "1":
                continue
            if cell.get("parent", "1") != "1":
                continue
            style = parse_style(cell.get("style", ""))
            if "swimlane" in style and get_geometry(cell) and get_geometry(cell)["w"] > 500:
                continue  # skip bands themselves
            if "text" in style:
                continue  # skip text/legend cells
            geom = get_geometry(cell)
            if not geom or geom["h"] == 0:
                continue
            # Check if this item overlaps any band's header
            for band_id, band_y, hdr_bot, band_x, band_right in band_headers:
                if band_x <= geom["x"] <= band_right and geom["y"] < hdr_bot:
                    if geom["y"] >= band_y:  # item starts inside this band's header
                        issues.append(
                            f"[{page_name}] INSIDE HEADER: '{cell.get('id', '')}' at y={int(geom['y'])} "
                            f"is inside '{band_id}' header (ends at y={int(hdr_bot)}). "
                            f"Move to y≥{int(hdr_bot) + 26}"
                        )
                        break

        # ─── Horizontal sibling overlap check ─────────────────────────────
        # Root-level items at similar y that overlap on x-axis
        root_items = []
        for cell in cells:
            if cell.get("vertex") != "1":
                continue
            if cell.get("parent", "1") != "1":
                continue
            style = parse_style(cell.get("style", ""))
            if "swimlane" in style and get_geometry(cell) and get_geometry(cell)["w"] > 500:
                continue
            if "text" in style:
                continue
            geom = get_geometry(cell)
            if not geom or geom["w"] == 0:
                continue
            root_items.append((cell.get("id", ""), geom["x"], geom["y"], geom["w"], geom["h"]))

        for i in range(len(root_items)):
            for j in range(i + 1, len(root_items)):
                id_a, xa, ya, wa, ha = root_items[i]
                id_b, xb, yb, wb, hb = root_items[j]
                # Check if they're in the same row (similar y)
                if abs(ya - yb) > max(ha, hb):
                    continue
                # Check x overlap
                overlap_x = min(xa + wa, xb + wb) - max(xa, xb)
                overlap_y = min(ya + ha, yb + hb) - max(ya, yb)
                if overlap_x > 5 and overlap_y > 5:
                    issues.append(
                        f"[{page_name}] HORIZONTAL OVERLAP: '{id_a}' and '{id_b}' "
                        f"overlap by {int(overlap_x)}×{int(overlap_y)}px"
                    )

        # ─── Step overlap detection ───────────────────────────────────────
        # Check if any children of the same parent overlap vertically
        parent_children = defaultdict(list)
        for cell in cells:
            if cell.get("vertex") != "1":
                continue
            parent_id = cell.get("parent", "1")
            if parent_id == "0" or parent_id == "1":
                continue
            geom = get_geometry(cell)
            if geom and geom["h"] > 0:
                parent_children[parent_id].append((cell.get("id", ""), geom["y"], geom["h"]))

        for parent_id, children in parent_children.items():
            # Sort by y position
            sorted_children = sorted(children, key=lambda c: c[1])
            for i in range(len(sorted_children) - 1):
                cid_a, y_a, h_a = sorted_children[i]
                cid_b, y_b, h_b = sorted_children[i + 1]
                if y_a + h_a > y_b:
                    overlap = y_a + h_a - y_b
                    issues.append(
                        f"[{page_name}] STEP OVERLAP: '{cid_a}' (bottom={int(y_a + h_a)}) "
                        f"overlaps '{cid_b}' (top={int(y_b)}) by {int(overlap)}px "
                        f"inside parent '{parent_id}'"
                    )

        # ─── Duplicate edge labels ────────────────────────────────────────
        edge_labels = defaultdict(list)
        for cell in cells:
            if cell.get("edge") != "1":
                continue
            value = cell.get("value", "").strip()
            if value and len(value) > 2:
                edge_labels[value].append(cell.get("id", ""))
        for label_text, edge_ids in edge_labels.items():
            if len(edge_ids) > 1:
                ids_str = ", ".join(edge_ids[:3])
                issues.append(
                    f"[{page_name}] DUPLICATE LABEL: '{label_text}' used on {len(edge_ids)} "
                    f"edges ({ids_str}) — differentiate them"
                )

        # ─── Content quality checks ──────────────────────────────────────
        # Thin labels: vertex boxes with only a short value (no <br/> = single line)
        for cell in cells:
            if cell.get("vertex") != "1":
                continue
            value = cell.get("value", "")
            style = parse_style(cell.get("style", ""))
            geom = get_geometry(cell)
            if not geom or geom["w"] == 0:
                continue
            # Skip legend, title, and text-only cells
            if "text" in style and style.get("fillColor", "none") == "none":
                continue
            # Skip swimlane band headers (they're just layer titles)
            if "swimlane" in style and geom["w"] > 500:
                continue
            # Check if content is too thin (no line breaks = probably just a filename)
            if value and "<br" not in value.lower() and len(value) > 3 and geom["h"] > 30:
                issues.append(
                    f"[{page_name}] THIN CONTENT: '{cell.get('id', '')}' has only "
                    f"'{value[:30]}' — add detail line with model/params/purpose"
                )

            # Text overflow check: estimate if text is wider than box
            if value and geom["w"] > 50:
                import re as _re
                text = _re.sub(r"<br\s*/?>", "\n", value, flags=_re.IGNORECASE)
                text = _re.sub(r"<[^>]+>", "", text)
                text = text.replace("&lt;", "<").replace("&gt;", ">")
                text = text.replace("&amp;", "&").replace("&quot;", '"')
                for line in text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    est_w = len(line) * 5.5 + 16
                    if est_w > geom["w"]:
                        issues.append(
                            f"[{page_name}] TEXT OVERFLOW: '{cell.get('id', '')}' "
                            f"line '{line[:40]}' (~{int(est_w)}px) in {int(geom['w'])}px box"
                        )
                        break  # one overflow per cell is enough

        # Oversized page check
        page_w_val = int(model.get("pageWidth", "827"))
        page_h_val = int(model.get("pageHeight", "1169"))
        if nodes:
            content_bottom = max(
                n["abs_y"] + n["h"] for n in nodes.values() if n["h"] > 0
            )
            if page_h_val > content_bottom + 200:
                issues.append(
                    f"[{page_name}] OVERSIZED PAGE: pageHeight={page_h_val} but "
                    f"content ends at y={int(content_bottom)}. "
                    f"Use layout.py page-size to fit."
                )

    return issues


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    filepath = sys.argv[1]
    issues = validate_file(filepath)

    if not issues:
        print("OK — no issues found")
    else:
        print(f"FOUND {len(issues)} ISSUE(S):\n")
        for issue in issues:
            print(f"  • {issue}")
        sys.exit(1)


if __name__ == "__main__":
    main()
