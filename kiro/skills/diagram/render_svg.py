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

def orthogonal_route(start, end, waypoints):
    """Convert point list to orthogonal (H/V only) segments.

    If waypoints are provided, they define the route.
    Otherwise, compute an L-shaped or Z-shaped orthogonal path.
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
                # Diagonal — insert an L-bend (go horizontal first)
                result.append((curr[0], prev[1]))
            result.append(curr)
        return result

    sx, sy = start
    ex, ey = end

    # No waypoints: create orthogonal route
    if abs(sx - ex) < 1:
        # Vertically aligned — straight line
        return [start, end]
    if abs(sy - ey) < 1:
        # Horizontally aligned — straight line
        return [start, end]

    # Determine dominant direction for L-routing
    dx = ex - sx
    dy = ey - sy

    if abs(dy) >= abs(dx):
        # Mostly vertical: go vertical first to midpoint, then horizontal, then vertical
        mid_y = sy + dy / 2
        return [(sx, sy), (sx, mid_y), (ex, mid_y), (ex, ey)]
    else:
        # Mostly horizontal: go horizontal to midpoint, then vertical, then horizontal
        mid_x = sx + dx / 2
        return [(sx, sy), (mid_x, sy), (mid_x, ey), (ex, ey)]


# ─── SVG rendering ───────────────────────────────────────────────────────────

def escape_xml(s):
    """Escape text for SVG XML content."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_swimlane(x, y, w, h, style, cell_id):
    """Render a swimlane: coloured header + light grey body."""
    fill = style.get("fillColor", "#ffe6cc")
    stroke = style.get("strokeColor", "#d79b00")
    stroke_w = style.get("strokeWidth", "1")
    start_size = int(style.get("startSize", "30"))
    dashed = style.get("dashed", "0") == "1"
    opacity = float(style.get("opacity", "100")) / 100.0

    dash_attr = ' stroke-dasharray="8 4"' if dashed else ""
    opacity_attr = f' opacity="{opacity}"' if opacity < 1.0 else ""

    # Handle fillColor=none (e.g., environment containers)
    if fill == "none" or fill == "":
        body_fill = "none"
        header_fill = "none"
    else:
        body_fill = "#fafafa"  # Light body
        header_fill = fill      # Saturated header

    parts = []
    # Body rectangle (full size, light background)
    parts.append(
        f'  <rect id="{cell_id}-body" x="{x:.1f}" y="{y:.1f}" '
        f'width="{w:.1f}" height="{h:.1f}" rx="4" ry="4" '
        f'fill="{body_fill}" stroke="{stroke}" stroke-width="{stroke_w}"{dash_attr}{opacity_attr} />'
    )
    # Header bar (coloured)
    if header_fill != "none":
        parts.append(
            f'  <rect id="{cell_id}-header" x="{x:.1f}" y="{y:.1f}" '
            f'width="{w:.1f}" height="{start_size:.1f}" rx="4" ry="4" '
            f'fill="{header_fill}" stroke="{stroke}" stroke-width="{stroke_w}"{dash_attr}{opacity_attr} />'
        )
        # Bottom corners of header should be square (overlap with body)
        parts.append(
            f'  <rect x="{x:.1f}" y="{y + start_size - 4:.1f}" '
            f'width="{w:.1f}" height="4.0" '
            f'fill="{header_fill}" stroke="none" />'
        )

    return "\n".join(parts)


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

    stroke = style.get("strokeColor", "#000000")
    stroke_w = style.get("strokeWidth", "2")
    dashed = style.get("dashed", "0") == "1"
    dash_pattern = style.get("dashPattern", "8 4")
    dash_attr = f' stroke-dasharray="{dash_pattern}"' if dashed else ""

    # Build polyline points string
    pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    # Arrowhead marker ID (unique per edge)
    marker_id = f"arrow-{cell_id}"

    parts = []
    # Define arrowhead marker
    parts.append(
        f'  <defs><marker id="{marker_id}" markerWidth="10" markerHeight="7" '
        f'refX="9" refY="3.5" orient="auto" markerUnits="strokeWidth">'
        f'<polygon points="0 0, 10 3.5, 0 7" fill="{stroke}" /></marker></defs>'
    )
    # Polyline (orthogonal segments)
    parts.append(
        f'  <polyline id="{cell_id}" points="{pts_str}" fill="none" '
        f'stroke="{stroke}" stroke-width="{stroke_w}"{dash_attr} '
        f'stroke-linejoin="round" marker-end="url(#{marker_id})" />'
    )

    # Label positioning: find a segment midpoint that doesn't overlap any box
    if label:
        lx, ly = _find_label_position(points, all_vertices)
        escaped = escape_xml(label)
        # White background behind label for readability
        text_w = len(label) * 6.5 + 4  # approximate
        parts.append(
            f'  <rect x="{lx - text_w/2:.1f}" y="{ly - 12:.1f}" '
            f'width="{text_w:.1f}" height="14" rx="2" ry="2" '
            f'fill="white" stroke="none" opacity="0.85" />'
        )
        parts.append(
            f'  <text x="{lx:.1f}" y="{ly - 2:.1f}" font-family="Inter, Arial, sans-serif" '
            f'font-size="10" text-anchor="middle" fill="{stroke}">{escaped}</text>'
        )

    return "\n".join(parts)


def _find_label_position(points, all_vertices):
    """Find a label position on the edge path that avoids overlapping boxes."""
    # Try midpoints of each segment, pick the one furthest from any box centre
    segments = []
    for i in range(len(points) - 1):
        mx = (points[i][0] + points[i + 1][0]) / 2
        my = (points[i][1] + points[i + 1][1]) / 2
        seg_len = ((points[i+1][0] - points[i][0])**2 + (points[i+1][1] - points[i][1])**2) ** 0.5
        segments.append((mx, my, seg_len))

    if not segments:
        return (points[0][0], points[0][1] - 8)

    # Score each midpoint: prefer longer segments and points far from box interiors
    best = segments[0]
    best_score = -1

    for mx, my, seg_len in segments:
        if seg_len < 15:
            continue  # Skip very short segments
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

        score = min_dist * 2 + seg_len * 0.5
        if score > best_score:
            best_score = score
            best = (mx, my, seg_len)

    return (best[0], best[1])


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

        # Render vertices
        svg_elements = []
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
                # Swimlanes get special two-tone rendering
                if "swimlane" in style:
                    svg_elements.append(
                        render_swimlane(v["x"], v["y"], v["w"], v["h"], style, cell_id)
                    )
                else:
                    svg_elements.append(
                        render_rect(v["x"], v["y"], v["w"], v["h"], style, cell_id)
                    )

            # Render text
            lines = html_to_text_lines(v["value"])
            if lines:
                # For swimlanes, text goes in the header area only
                if "swimlane" in style:
                    start_size = int(style.get("startSize", "30"))
                    text_svg = render_text(
                        v["x"], v["y"], v["w"], start_size, lines, style, f"{cell_id}-text"
                    )
                else:
                    text_svg = render_text(
                        v["x"], v["y"], v["w"], v["h"], lines, style, f"{cell_id}-text"
                    )
                if text_svg:
                    svg_texts.append(text_svg)

        # Second pass: edges
        svg_edges = []
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

            # Build orthogonal route
            points = orthogonal_route(start, end, waypoints)

            # Get label
            label_text = html_to_plain(value)

            svg_edges.append(render_edge(points, style, label_text, cell_id, vertices))

        # Assemble page SVG
        # Compute actual bounds from content
        min_x = min((v["x"] for v in vertices.values()), default=0)
        min_y = min((v["y"] for v in vertices.values()), default=0)
        max_x = max((v["x"] + v["w"] for v in vertices.values()), default=page_w)
        max_y = max((v["y"] + v["h"] for v in vertices.values()), default=page_h)

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

        # Edges first (behind boxes)
        page_svg.extend(svg_edges)
        # Then boxes
        page_svg.extend(svg_elements)
        # Then text (on top)
        page_svg.extend(svg_texts)

        page_svg.append('</svg>')
        all_pages_svg.append("\n".join(page_svg))

    # If multiple pages, wrap in a container SVG or return first page
    if len(all_pages_svg) == 1:
        return all_pages_svg[0]
    else:
        # Return each page as a separate SVG separated by a comment
        return "\n\n".join(
            f"<!-- Page {i+1} -->\n{svg}"
            for i, svg in enumerate(all_pages_svg)
        )


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    svg_content = convert_drawio_to_svg(input_path)

    if output_path:
        with open(output_path, "w") as f:
            f.write(svg_content)
        print(f"Wrote SVG to {output_path}")
    else:
        print(svg_content)


if __name__ == "__main__":
    main()
