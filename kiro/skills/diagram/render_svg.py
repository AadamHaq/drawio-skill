#!/usr/bin/env python3
"""Convert a .drawio XML file to SVG. No third-party packages required.

Reads mxCell elements (vertices and edges), resolves parent offsets,
and outputs a self-contained SVG with rectangles, text, and orthogonal edges.

Usage:
  render_svg.py <input.drawio> [output.svg]

If output is omitted, writes to stdout.

Features:
- Orthogonal edge routing (right-angle segments only, matching draw.io behaviour)
- Swimlane rendering: coloured header bar + light body background
- Edge label collision avoidance (offset labels away from box borders)
- HTML tag parsing (<br/>, <b>, <i>, <font>) in text rendering
- Rounded/dashed rectangles, cylinders (as rounded rects)
- Arrowhead markers per edge colour

Limitations:
- Does not support images, custom shapes, or complex stencils
- Font metrics are approximate (no kerning)
- Multi-page files produce concatenated SVGs
"""

import re
import sys
import xml.etree.ElementTree as ET


# ─── Style parsing ───────────────────────────────────────────────────────────

def parse_style(style_str):
    """Parse draw.io style string into a dict."""
    result = {}
    if not style_str:
        return result
    for part in style_str.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            result[k.strip()] = v.strip()
        elif part.strip():
            result[part.strip()] = "1"
    return result


def html_to_text_lines(value):
    """Convert draw.io HTML value to plain text lines with style hints.

    Returns list of (text, bold, italic) tuples per line.
    """
    if not value:
        return []
    # Replace <br/> and <br> with newline
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    # Track bold/italic state from tags (simplified: per-line)
    # Remove font/colour tags but note style tags
    has_bold = bool(re.search(r"<b>|fontStyle.*?1", text, re.IGNORECASE))
    has_italic = bool(re.search(r"<i>|<em>", text, re.IGNORECASE))
    # Strip all HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode common HTML entities
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&amp;", "&").replace("&quot;", '"')
    text = text.replace("&#xa;", "\n")
    lines = text.split("\n")
    return [l.strip() for l in lines if l.strip()]


def html_to_plain(value):
    """Simple HTML→plain text for edge labels."""
    if not value:
        return ""
    text = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&amp;", "&").replace("&quot;", '"')
    return text.strip()


# ─── Geometry helpers ────────────────────────────────────────────────────────

def get_geometry(cell):
    """Extract geometry from mxCell → mxGeometry."""
    geom = cell.find("mxGeometry")
    if geom is None:
        return None
    return {
        "x": float(geom.get("x", 0)),
        "y": float(geom.get("y", 0)),
        "w": float(geom.get("width", 0)),
        "h": float(geom.get("height", 0)),
        "relative": geom.get("relative", "0") == "1",
    }


def get_waypoints(cell):
    """Extract waypoints from edge geometry."""
    geom = cell.find("mxGeometry")
    if geom is None:
        return []
    array = geom.find("Array")
    if array is None:
        return []
    points = []
    for pt in array.findall("mxPoint"):
        points.append((float(pt.get("x", 0)), float(pt.get("y", 0))))
    return points


# ─── Orthogonal edge routing ─────────────────────────────────────────────────

def orthogonal_route(start, end, waypoints, exit_x=0.5, exit_y=1.0):
    """Convert point list to orthogonal (H/V only) segments.

    If waypoints are provided, they define the route.
    Otherwise, compute a route based on exit direction:
    - exitY=1 or exitY=0 (top/bottom exit): first move is VERTICAL (↓→↓ Z-pattern)
    - exitX=0 or exitX=1 (side exit): first move is HORIZONTAL (→↓→ Z-pattern)
    """
    if waypoints:
        # Waypoints already define the orthogonal path
        all_pts = [start] + list(waypoints) + [end]
        # Ensure segments are orthogonal by inserting corner points
        result = [all_pts[0]]
        for i in range(1, len(all_pts)):
            prev = result[-1]
            curr = all_pts[i]
            if abs(prev[0] - curr[0]) > 1 and abs(prev[1] - curr[1]) > 1:
                # Diagonal — need an L-bend
                if i == len(all_pts) - 1:
                    # Last point: approach correctly for entry direction
                    if abs(curr[1] - prev[1]) >= abs(curr[0] - prev[0]):
                        result.append((curr[0], prev[1]))
                    else:
                        result.append((prev[0], curr[1]))
                else:
                    if abs(curr[1] - prev[1]) >= abs(curr[0] - prev[0]):
                        result.append((prev[0], curr[1]))
                    else:
                        result.append((curr[0], prev[1]))
            result.append(curr)
        return result

    sx, sy = start
    ex, ey = end

    # No waypoints: create orthogonal route
    if abs(sx - ex) < 1:
        return [start, end]  # Vertically aligned
    if abs(sy - ey) < 1:
        return [start, end]  # Horizontally aligned

    dx = ex - sx
    dy = ey - sy

    # Determine exit direction from exit_x/exit_y:
    # exitY in (0, 1) with exitX near 0.5 → exiting top/bottom (vertical first)
    # exitX in (0, 1) with exitY near 0.5 → exiting left/right (horizontal first)
    exits_vertically = (exit_y in (0.0, 1.0)) and (0.15 < exit_x < 0.85)
    exits_horizontally = (exit_x in (0.0, 1.0)) and (0.15 < exit_y < 0.85)

    if exits_horizontally:
        # Side exit: go HORIZONTAL first, then vertical, then horizontal to target
        # Pattern: → ↓ → (or ← ↓ ←)
        mid_x = sx + dx / 2
        return [(sx, sy), (mid_x, sy), (mid_x, ey), (ex, ey)]
    else:
        # Top/bottom exit (default): go VERTICAL first, then horizontal, then vertical
        # Pattern: ↓ → ↓ (or ↑ → ↑)
        # Bias jog toward source (1/3) so it stays in the gap between bands
        # and doesn't land inside the next band's header zone.
        mid_y = sy + dy * 0.33
        return [(sx, sy), (sx, mid_y), (ex, mid_y), (ex, ey)]


# ─── SVG rendering ───────────────────────────────────────────────────────────

def escape_xml(s):
    """Escape text for SVG XML content."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_swimlane(x, y, w, h, style, cell_id):
    """Render a swimlane: coloured header + light grey body (combined)."""
    body, header = render_swimlane_split(x, y, w, h, style, cell_id)
    return body + "\n" + header


def render_swimlane_split(x, y, w, h, style, cell_id):
    """Render a swimlane as two separate SVG strings: (body, header).

    Body renders behind edges; header renders on top of edges to cover crossings.
    """
    fill = style.get("fillColor", "#ffe6cc")
    stroke = style.get("strokeColor", "#d79b00")
    stroke_w = style.get("strokeWidth", "1")
    start_size = int(style.get("startSize", "30"))
    dashed = style.get("dashed", "0") == "1"
    opacity = float(style.get("opacity", "100")) / 100.0

    dash_attr = ' stroke-dasharray="8 4"' if dashed else ""
    opacity_attr = f' opacity="{opacity}"' if opacity < 1.0 else ""

    if fill == "none" or fill == "":
        body_fill = "none"
        header_fill = "none"
    elif dashed:
        body_fill = fill
        header_fill = fill
    else:
        body_fill = "#fafafa"
        # Header fill: use the declared fill. For near-white fills (like #f9f9f9),
        # the header still masks edge crossings because it renders on top at full opacity.
        # Use the body_fill (#fafafa) as a minimum to ensure edges are hidden.
        header_fill = fill if fill != "#f9f9f9" else "#f0f0f0"

    # Body rectangle (full size, light background)
    body_svg = (
        f'  <rect id="{cell_id}-body" x="{x:.1f}" y="{y:.1f}" '
        f'width="{w:.1f}" height="{h:.1f}" rx="4" ry="4" '
        f'fill="{body_fill}" stroke="{stroke}" stroke-width="{stroke_w}"{dash_attr}{opacity_attr} />'
    )

    # Header bar (coloured, rendered ON TOP of edges)
    header_parts = []
    if header_fill != "none":
        header_parts.append(
            f'  <rect id="{cell_id}-header" x="{x:.1f}" y="{y:.1f}" '
            f'width="{w:.1f}" height="{start_size:.1f}" rx="4" ry="4" '
            f'fill="{header_fill}" stroke="{stroke}" stroke-width="{stroke_w}"{dash_attr}{opacity_attr} />'
        )
        # Square bottom corners of header (overlap cover)
        header_parts.append(
            f'  <rect x="{x:.1f}" y="{y + start_size - 4:.1f}" '
            f'width="{w:.1f}" height="4.0" '
            f'fill="{header_fill}" stroke="none" />'
        )
    header_svg = "\n".join(header_parts)

    return body_svg, header_svg


def render_rect(x, y, w, h, style, cell_id):
    """Render a rectangle (possibly rounded) as SVG."""
    fill = style.get("fillColor", "#ffffff")
    stroke = style.get("strokeColor", "#000000")
    stroke_w = style.get("strokeWidth", "1")
    rounded = style.get("rounded", "0") == "1"
    dashed = style.get("dashed", "0") == "1"
    opacity = float(style.get("opacity", "100")) / 100.0

    rx = "8" if rounded else "0"
    dash_attr = ' stroke-dasharray="8 4"' if dashed else ""
    opacity_attr = f' opacity="{opacity}"' if opacity < 1.0 else ""

    if fill == "none" or fill == "":
        fill_attr = 'fill="none"'
    else:
        fill_attr = f'fill="{fill}"'

    return (
        f'  <rect id="{cell_id}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'rx="{rx}" ry="{rx}" {fill_attr} stroke="{stroke}" '
        f'stroke-width="{stroke_w}"{dash_attr}{opacity_attr} />'
    )


def render_text(x, y, w, h, lines, style, cell_id):
    """Render text lines centred in a box."""
    if not lines:
        return ""

    font_size = int(style.get("fontSize", "11"))
    font_style_val = style.get("fontStyle", "0")
    try:
        fs_int = int(font_style_val)
    except ValueError:
        fs_int = 0
    bold = fs_int & 1
    italic = fs_int & 2
    v_align = style.get("verticalAlign", "middle")
    align = style.get("align", "center")

    weight = "bold" if bold else "normal"
    font_style = "italic" if italic else "normal"

    # Text anchor
    if align == "left":
        anchor = "start"
        tx = x + 6
    elif align == "right":
        anchor = "end"
        tx = x + w - 6
    else:
        anchor = "middle"
        tx = x + w / 2

    # Vertical positioning
    line_height = font_size + 4
    total_text_h = len(lines) * line_height

    if v_align == "top":
        start_y = y + font_size + 4
    elif v_align == "bottom":
        start_y = y + h - total_text_h + font_size
    else:  # middle
        start_y = y + (h - total_text_h) / 2 + font_size

    parts = []
    for i, line in enumerate(lines):
        ty = start_y + i * line_height
        escaped = escape_xml(line)
        parts.append(
            f'  <text x="{tx:.1f}" y="{ty:.1f}" font-family="Inter, Arial, sans-serif" '
            f'font-size="{font_size}" font-weight="{weight}" font-style="{font_style}" '
            f'text-anchor="{anchor}" fill="#333">{escaped}</text>'
        )
    return "\n".join(parts)


def render_edge(points, style, label, cell_id, all_vertices):
    """Render an edge as orthogonal polyline with arrowhead and positioned label."""
    if len(points) < 2:
        return ""

    # Clean up the point list: remove consecutive duplicates and zero-length segments
    cleaned = [points[0]]
    for i in range(1, len(points)):
        px, py = cleaned[-1]
        cx, cy = points[i]
        if abs(px - cx) > 0.5 or abs(py - cy) > 0.5:
            cleaned.append(points[i])
    points = cleaned

    if len(points) < 2:
        return ""

    # Ensure the final segment has meaningful length for arrowhead orientation.
    # If the last two points are very close, extend back to find a directional segment.
    last_seg_len = ((points[-1][0] - points[-2][0])**2 + (points[-1][1] - points[-2][1])**2) ** 0.5
    if last_seg_len < 2 and len(points) > 2:
        # Remove the near-duplicate penultimate point
        points = points[:-2] + [points[-1]]

    stroke = style.get("strokeColor", "#000000")
    stroke_w = style.get("strokeWidth", "2")
    dashed = style.get("dashed", "0") == "1"
    dash_pattern = style.get("dashPattern", "8 4")
    dash_attr = f' stroke-dasharray="{dash_pattern}"' if dashed else ""

    # Build polyline points string
    pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    # Arrowhead marker ID (unique per edge)
    marker_id = f"arrow-{cell_id}"

    # Determine arrowhead size relative to stroke width
    # Use userSpaceOnUse for consistent sizing regardless of stroke width
    parts = []
    parts.append(
        f'  <defs><marker id="{marker_id}" markerWidth="10" markerHeight="8" '
        f'refX="9" refY="4" orient="auto" markerUnits="userSpaceOnUse">'
        f'<polygon points="0 0, 10 4, 0 8" fill="{stroke}" /></marker></defs>'
    )
    # Polyline (orthogonal segments)
    parts.append(
        f'  <polyline id="{cell_id}" points="{pts_str}" fill="none" '
        f'stroke="{stroke}" stroke-width="{stroke_w}"{dash_attr} '
        f'stroke-linejoin="round" marker-end="url(#{marker_id})" />'
    )

    # Label positioning
    if label:
        # Compute the edge's total path length
        edge_total_len = sum(
            ((points[i+1][0] - points[i][0])**2 + (points[i+1][1] - points[i][1])**2) ** 0.5
            for i in range(len(points) - 1)
        )
        text_w = len(label) * 6.5 + 8  # approximate width

        lx, ly, label_above, text_anchor = _find_label_position(points, all_vertices, label)
        escaped = escape_xml(label)
        text_h = 14

        # For labels wider than the edge: place them offset (above/below with no pill)
        # For labels that fit: place with capped pill
        if text_w > edge_total_len - 10:
            # Label is wider than edge — render as offset text, no pill background
            parts.append(
                f'  <text x="{lx:.1f}" y="{ly - 8:.1f}" font-family="Inter, Arial, sans-serif" '
                f'font-size="9" text-anchor="{text_anchor}" fill="{stroke}" '
                f'font-style="italic">{escaped}</text>'
            )
        else:
            # Cap pill width to edge length
            pill_w = min(text_w, edge_total_len - 10)

            if label_above:
                rect_y = ly - text_h - 4
                text_y = ly - 6
            else:
                rect_y = ly - text_h + 2
                text_y = ly - 2

            # For dashed edges, use lower opacity so dashes stay visible
            pill_opacity = "0.6" if dashed else "0.9"

            # Pill x position depends on anchor
            if text_anchor == "start":
                pill_x = lx - 2  # small padding before text start
            else:
                pill_x = lx - pill_w / 2

            parts.append(
                f'  <rect x="{pill_x:.1f}" y="{rect_y:.1f}" '
                f'width="{pill_w:.1f}" height="{text_h}" rx="2" ry="2" '
                f'fill="white" stroke="none" opacity="{pill_opacity}" />'
            )
            parts.append(
                f'  <text x="{lx:.1f}" y="{text_y:.1f}" font-family="Inter, Arial, sans-serif" '
                f'font-size="10" text-anchor="{text_anchor}" fill="{stroke}">{escaped}</text>'
            )

    return "\n".join(parts)


def _find_label_position(points, all_vertices, label=""):
    """Find a label position on the edge path that avoids overlapping boxes.

    Returns (x, y, label_above) where label_above=True means the label should
    be placed above the segment rather than centred on it.
    """
    # Compute text width estimate
    text_w = len(label) * 6.5 + 8 if label else 50

    # Try midpoints of each segment, pick the one furthest from any box centre
    segments = []
    for i in range(len(points) - 1):
        mx = (points[i][0] + points[i + 1][0]) / 2
        my = (points[i][1] + points[i + 1][1]) / 2
        seg_len = ((points[i+1][0] - points[i][0])**2 + (points[i+1][1] - points[i][1])**2) ** 0.5
        # Determine if segment is horizontal or vertical
        is_horizontal = abs(points[i][1] - points[i+1][1]) < 1
        segments.append((mx, my, seg_len, is_horizontal))

    if not segments:
        return (points[0][0], points[0][1] - 12, True, "middle")

    # Score each midpoint: prefer longer segments, avoid box interiors
    best = None
    best_score = -1

    for mx, my, seg_len, is_horizontal in segments:
        if seg_len < 8:
            continue  # Skip tiny segments

        # Distance to nearest box border
        min_dist = 999
        for v in all_vertices.values():
            if v["w"] == 0 or v["h"] == 0:
                continue
            # Check if point is inside box
            if v["x"] < mx < v["x"] + v["w"] and v["y"] < my < v["y"] + v["h"]:
                min_dist = 0
                break
            # Distance to nearest edge of box
            dx = max(v["x"] - mx, 0, mx - (v["x"] + v["w"]))
            dy = max(v["y"] - my, 0, my - (v["y"] + v["h"]))
            dist = (dx**2 + dy**2) ** 0.5
            min_dist = min(min_dist, dist)

        # Bonus for segments long enough to fit the label
        length_bonus = 20 if seg_len >= text_w else 0
        # Strong preference for longer segments — avoids picking tiny jogs
        score = min_dist * 2 + seg_len * 1.5 + length_bonus
        if score > best_score:
            best_score = score
            best = (mx, my, seg_len, is_horizontal)

    if best is None:
        # Fallback: first segment midpoint, above
        mx = (points[0][0] + points[1][0]) / 2
        my = (points[0][1] + points[1][1]) / 2
        return (mx, my - 12, True, "middle")

    mx, my, seg_len, is_horizontal = best

    # If the segment is shorter than the label text, position label above/below
    label_above = seg_len < text_w

    # Check if placing the label above would collide with a box
    if label_above and is_horizontal:
        label_rect_top = my - 18  # approx: 14px height + 4px gap
        label_rect_bottom = my - 4
        label_half_w = text_w / 2
        collision_above = False
        collision_below = False
        for v in all_vertices.values():
            if v["w"] == 0 or v["h"] == 0:
                continue
            # Check above position
            if (v["x"] < mx + label_half_w and v["x"] + v["w"] > mx - label_half_w
                    and v["y"] < label_rect_bottom and v["y"] + v["h"] > label_rect_top):
                collision_above = True
            # Check below position
            below_top = my + 4
            below_bottom = my + 18
            if (v["x"] < mx + label_half_w and v["x"] + v["w"] > mx - label_half_w
                    and v["y"] < below_bottom and v["y"] + v["h"] > below_top):
                collision_below = True

        if collision_above and not collision_below:
            # Place below instead
            my = my + 14
            label_above = False  # Signal: use "below" positioning
        elif collision_above and collision_below:
            # Both collide — place centred on the edge line with white bg
            label_above = False
        # else: above is fine, keep label_above = True

    if is_horizontal and label_above:
        my = my - 4  # Will be offset further by the caller
        return (mx, my, label_above, "middle")
    elif not is_horizontal:
        # For vertical edges: position label to the right of the line, left-aligned.
        # Use 12px offset for dashed edges (wider visual stroke), 8px for solid.
        offset = 12
        mx = mx + offset
        label_above = False
        return (mx, my, label_above, "start")

    # Additional check: if the overall edge is mostly vertical (start-to-end),
    # offset label to the right even if the best segment happened to be horizontal
    overall_dx = abs(points[-1][0] - points[0][0])
    overall_dy = abs(points[-1][1] - points[0][1])
    if overall_dy > overall_dx * 2 and is_horizontal:
        edge_center_x = (points[0][0] + points[-1][0]) / 2
        mx = edge_center_x + 8
        label_above = False
        return (mx, my, label_above, "start")

    return (mx, my, label_above, "middle")

    return (mx, my, label_above)


# ─── Main conversion ─────────────────────────────────────────────────────────

def convert_drawio_to_svg(drawio_path):
    """Parse a .drawio file and return SVG string."""
    tree = ET.parse(drawio_path)
    root = tree.getroot()

    diagrams = root.findall("diagram")
    if not diagrams:
        return "<!-- No diagrams found -->"

    all_pages_svg = []

    for diagram in diagrams:
        page_name = diagram.get("name", "Page")
        model = diagram.find("mxGraphModel")
        if model is None:
            continue

        page_w = int(model.get("pageWidth", "827"))
        page_h = int(model.get("pageHeight", "1169"))
        root_elem = model.find("root")
        if root_elem is None:
            continue

        cells = root_elem.findall("mxCell")

        # Build parent offset map
        parent_offsets = {"0": (0, 0), "1": (0, 0)}
        vertices = {}  # id -> {x, y, w, h, style, value, parent}

        # First pass: collect all vertices and compute offsets
        for cell in cells:
            if cell.get("vertex") != "1":
                continue
            cell_id = cell.get("id", "")
            parent = cell.get("parent", "1")
            geom = get_geometry(cell)
            if not geom:
                continue

            off_x, off_y = parent_offsets.get(parent, (0, 0))
            abs_x = geom["x"] + off_x
            abs_y = geom["y"] + off_y

            vertices[cell_id] = {
                "x": abs_x, "y": abs_y,
                "w": geom["w"], "h": geom["h"],
                "style": parse_style(cell.get("style", "")),
                "value": cell.get("value", ""),
                "parent": parent,
            }
            # Register as potential parent
            parent_offsets[cell_id] = (abs_x, abs_y)

        # Render vertices — split into bodies (background) and headers (foreground)
        svg_bodies = []    # Band body rects, regular rects, sub-step rects
        svg_headers = []   # Swimlane header bars (render AFTER edges to cover crossings)
        svg_texts = []

        for cell_id, v in vertices.items():
            style = v["style"]
            # Skip if it's just a text cell with no dimensions
            if v["w"] == 0 and v["h"] == 0:
                continue

            # Determine if this is a text-only cell
            is_text_only = (
                "text" in style
                and style.get("fillColor", "none") == "none"
                and style.get("strokeColor", "none") == "none"
            )

            if not is_text_only:
                # Swimlanes get special two-tone rendering (body separate from header)
                if "swimlane" in style:
                    body_svg, header_svg = render_swimlane_split(
                        v["x"], v["y"], v["w"], v["h"], style, cell_id
                    )
                    svg_bodies.append(body_svg)
                    svg_headers.append(header_svg)
                else:
                    svg_bodies.append(
                        render_rect(v["x"], v["y"], v["w"], v["h"], style, cell_id)
                    )

            # Render text
            lines = html_to_text_lines(v["value"])
            if lines:
                # For swimlanes, text goes in the header area only
                if "swimlane" in style:
                    start_size = int(style.get("startSize", "30"))
                    # Dashed containers need more top padding for title
                    is_dashed = style.get("dashed", "0") == "1"
                    title_h = start_size
                    title_y = v["y"]
                    if is_dashed:
                        title_y += 4  # Extra padding from top border
                    text_svg = render_text(
                        v["x"], title_y, v["w"], title_h, lines, style, f"{cell_id}-text"
                    )
                else:
                    text_svg = render_text(
                        v["x"], v["y"], v["w"], v["h"], lines, style, f"{cell_id}-text"
                    )
                if text_svg:
                    svg_texts.append(text_svg)

        # Second pass: edges
        svg_edges = []  # (svg_string, total_path_length)
        for cell in cells:
            if cell.get("edge") != "1":
                continue
            cell_id = cell.get("id", "")
            source_id = cell.get("source", "")
            target_id = cell.get("target", "")
            style = parse_style(cell.get("style", ""))
            value = cell.get("value", "")
            parent = cell.get("parent", "1")

            off_x, off_y = parent_offsets.get(parent, (0, 0))

            # Compute start point
            start = None
            if source_id in vertices:
                src = vertices[source_id]
                exit_x = float(style.get("exitX", "0.5"))
                exit_y = float(style.get("exitY", "1"))
                sx = src["x"] + src["w"] * exit_x
                sy = src["y"] + src["h"] * exit_y
                start = (sx, sy)

            # Compute end point
            end = None
            if target_id in vertices:
                tgt = vertices[target_id]
                entry_x = float(style.get("entryX", "0.5"))
                entry_y = float(style.get("entryY", "0"))
                ex = tgt["x"] + tgt["w"] * entry_x
                ey = tgt["y"] + tgt["h"] * entry_y
                end = (ex, ey)

            if not start or not end:
                continue

            # Get explicit waypoints
            waypoints = get_waypoints(cell)
            waypoints = [(wx + off_x, wy + off_y) for wx, wy in waypoints]

            # Build orthogonal route — pass exit direction for smart routing
            exit_x_val = float(style.get("exitX", "0.5"))
            exit_y_val = float(style.get("exitY", "1"))
            points = orthogonal_route(start, end, waypoints,
                                      exit_x=exit_x_val, exit_y=exit_y_val)

            # Approach direction fix: If the final segment is horizontal but
            # arrives AT the target's top/bottom edge, insert a vertical approach.
            if len(points) >= 2 and target_id in vertices:
                entry_y_val = float(style.get("entryY", "0"))
                last_pt = points[-1]
                pen_pt = points[-2]

                last_is_horizontal = abs(last_pt[1] - pen_pt[1]) < 1
                last_seg_len = ((last_pt[0] - pen_pt[0])**2 + (last_pt[1] - pen_pt[1])**2) ** 0.5

                # Only fix if the final segment is horizontal AND non-trivial (>10px)
                # AND the entry is at top (entryY=0) or bottom (entryY=1)
                if last_is_horizontal and last_seg_len > 10 and entry_y_val in (0.0, 1.0):
                    # The edge is arriving horizontally at the target's top/bottom — bad.
                    # Insert a jog: end the horizontal 8px above/below target, then go vertical.
                    clearance = 8
                    if entry_y_val == 0:
                        jog_y = last_pt[1] - clearance
                    else:
                        jog_y = last_pt[1] + clearance

                    # Rewrite: ... → pen_pt → (last_x, jog_y) shifted up → (last_x, pen_y as jog) → last_pt
                    # Actually simpler: just move the horizontal jog above and add vertical approach
                    points = points[:-2] + [(pen_pt[0], jog_y), (last_pt[0], jog_y), last_pt]

            # Get label
            label_text = html_to_plain(value)

            edge_svg = render_edge(points, style, label_text, cell_id, vertices)
            # Compute total path length for z-ordering
            total_len = sum(
                ((points[i+1][0] - points[i][0])**2 + (points[i+1][1] - points[i][1])**2) ** 0.5
                for i in range(len(points) - 1)
            )
            svg_edges.append((edge_svg, total_len, target_id))

        # Assemble page SVG
        # Compute actual bounds from content
        min_x = min((v["x"] for v in vertices.values()), default=0)
        min_y = min((v["y"] for v in vertices.values()), default=0)
        max_x = max((v["x"] + v["w"] for v in vertices.values()), default=page_w)
        max_y = max((v["y"] + v["h"] for v in vertices.values()), default=page_h)

        # Include edge waypoints in bounds (they may route outside vertex area)
        import re as _re_bounds
        for edge_svg, _, _ in svg_edges:
            for match in _re_bounds.finditer(r'points="([^"]+)"', edge_svg):
                for pt in match.group(1).split():
                    coords = pt.split(",")
                    if len(coords) == 2 and coords[0] and coords[1]:
                        try:
                            px, py = float(coords[0]), float(coords[1])
                            min_x = min(min_x, px)
                            min_y = min(min_y, py)
                            max_x = max(max_x, px)
                            max_y = max(max_y, py)
                        except ValueError:
                            pass

        # Add margin
        margin = 20
        vb_x = min_x - margin
        vb_y = min_y - margin
        vb_w = (max_x - min_x) + 2 * margin
        vb_h = (max_y - min_y) + 2 * margin

        page_svg = []
        page_svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
                       f'viewBox="{vb_x:.0f} {vb_y:.0f} {vb_w:.0f} {vb_h:.0f}" '
                       f'width="{vb_w:.0f}" height="{vb_h:.0f}">')
        page_svg.append(f'  <!-- Page: {escape_xml(page_name)} -->')
        page_svg.append('  <style>text { font-family: Inter, Arial, sans-serif; }</style>')

        # Z-order: bodies → headers → ALL edges → text
        # Headers render before edges so they provide the coloured band fill.
        # ALL edges render on top (visible, with labels uncovered).
        # The skill rules (waypoints, 26px clearance) prevent edges from
        # crossing through headers at authoring time — we don't need z-order
        # tricks to hide them anymore.
        page_svg.extend(svg_bodies)
        page_svg.extend(svg_headers)
        for edge_svg, _, _ in svg_edges:
            page_svg.append(edge_svg)
        page_svg.extend(svg_texts)

        page_svg.append('</svg>')
        all_pages_svg.append("\n".join(page_svg))

    # If multiple pages, wrap in a container SVG or return first page
    # For multiple pages, return a list of (page_name, svg_content) tuples
    if len(all_pages_svg) == 1:
        return all_pages_svg[0]
    else:
        return all_pages_svg


def _page_filename(base_path, page_index, total_pages):
    """Generate filename for a specific page: base_p1.svg, base_p2.svg, etc."""
    if total_pages == 1:
        return base_path
    stem = base_path.rsplit(".", 1)[0] if "." in base_path else base_path
    return f"{stem}_p{page_index + 1}.svg"


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    result = convert_drawio_to_svg(input_path)

    if isinstance(result, str):
        # Single page
        if output_path:
            with open(output_path, "w") as f:
                f.write(result)
            print(f"Wrote SVG to {output_path}")
        else:
            print(result)
    else:
        # Multiple pages — write separate files
        if output_path:
            for i, page_svg in enumerate(result):
                page_file = _page_filename(output_path, i, len(result))
                with open(page_file, "w") as f:
                    f.write(page_svg)
                print(f"Wrote page {i+1} to {page_file}")
        else:
            # To stdout: separate with comments (for piping)
            for i, page_svg in enumerate(result):
                print(f"<!-- Page {i+1} -->")
                print(page_svg)
                print()


if __name__ == "__main__":
    main()
