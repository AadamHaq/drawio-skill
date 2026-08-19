#!/usr/bin/env python3
"""Convert a .drawio XML file to SVG. No third-party packages required.

Reads mxCell elements (vertices and edges), resolves parent offsets,
and outputs a self-contained SVG with rectangles, text, and polyline edges.

Usage:
  render_svg.py <input.drawio> [output.svg]

If output is omitted, writes to stdout.

Limitations:
- Renders rectangles (rounded or sharp), cylinders (as rounded rects), and text
- Edge routing uses waypoints from the XML (does not re-route)
- Does not support images, custom shapes, or complex stencils
- Font metrics are approximate (monospace-based width estimation)
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
    """Convert draw.io HTML value to plain text lines."""
    if not value:
        return []
    # Replace <br/> and <br> with newline
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode common HTML entities
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&amp;", "&").replace("&quot;", '"')
    text = text.replace("&#xa;", "\n")
    lines = text.split("\n")
    return [l.strip() for l in lines if l.strip()]


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


# ─── SVG rendering ───────────────────────────────────────────────────────────

def escape_xml(s):
    """Escape text for SVG XML content."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


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
    font_style = style.get("fontStyle", "0")
    bold = int(font_style) & 1
    italic = int(font_style) & 2
    v_align = style.get("verticalAlign", "middle")
    align = style.get("align", "center")

    weight = "bold" if bold else "normal"
    style_attr = "italic" if italic else "normal"

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
            f'font-size="{font_size}" font-weight="{weight}" font-style="{style_attr}" '
            f'text-anchor="{anchor}" fill="#333">{escaped}</text>'
        )
    return "\n".join(parts)


def render_edge(points, style, label, cell_id):
    """Render an edge as a polyline with optional arrowhead and label."""
    if len(points) < 2:
        return ""

    stroke = style.get("strokeColor", "#000000")
    stroke_w = style.get("strokeWidth", "2")
    dashed = style.get("dashed", "0") == "1"
    dash_attr = ' stroke-dasharray="8 4"' if dashed else ""

    # Build polyline points string
    pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    # Arrowhead marker ID (unique per colour)
    marker_id = f"arrow-{cell_id}"

    parts = []
    # Define arrowhead marker
    parts.append(
        f'  <defs><marker id="{marker_id}" markerWidth="8" markerHeight="6" '
        f'refX="8" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" '
        f'fill="{stroke}" /></marker></defs>'
    )
    # Polyline
    parts.append(
        f'  <polyline id="{cell_id}" points="{pts_str}" fill="none" '
        f'stroke="{stroke}" stroke-width="{stroke_w}"{dash_attr} '
        f'marker-end="url(#{marker_id})" />'
    )

    # Label at midpoint
    if label:
        mid_idx = len(points) // 2
        if mid_idx < len(points):
            lx, ly = points[mid_idx]
        else:
            lx = (points[0][0] + points[-1][0]) / 2
            ly = (points[0][1] + points[-1][1]) / 2
        escaped = escape_xml(label)
        parts.append(
            f'  <text x="{lx:.1f}" y="{ly - 6:.1f}" font-family="Inter, Arial, sans-serif" '
            f'font-size="10" text-anchor="middle" fill="{stroke}">{escaped}</text>'
        )

    return "\n".join(parts)


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
            points = []
            if source_id in vertices:
                src = vertices[source_id]
                exit_x = float(style.get("exitX", "0.5"))
                exit_y = float(style.get("exitY", "1"))
                sx = src["x"] + src["w"] * exit_x
                sy = src["y"] + src["h"] * exit_y
                points.append((sx, sy))

            # Add waypoints
            waypoints = get_waypoints(cell)
            for wx, wy in waypoints:
                points.append((wx + off_x, wy + off_y))

            # Compute end point
            if target_id in vertices:
                tgt = vertices[target_id]
                entry_x = float(style.get("entryX", "0.5"))
                entry_y = float(style.get("entryY", "0"))
                ex = tgt["x"] + tgt["w"] * entry_x
                ey = tgt["y"] + tgt["h"] * entry_y
                points.append((ex, ey))

            if len(points) >= 2:
                label = html_to_text_lines(value)
                label_text = label[0] if label else ""
                svg_edges.append(render_edge(points, style, label_text, cell_id))

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
