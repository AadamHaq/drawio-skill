# Pipeline Rendering Strategy

Use this for PIPELINE topology repos.

## Page Structure

Generate 2-4 pages:
1. **Overview** (portrait 827×1169) — all stages as swimlanes with internal steps visible
2. **Drill-down pages** — one per complex stage (≥3 sub-steps or has loops)

## Overview Page Layout

- **Row 0**: Input nodes at y=30, centred horizontally
- **Row 1+**: One row per sequential stage; parallel stages side-by-side
- **Last row**: Output nodes

### Input node ordering
Order inputs to match their target stages: input feeding the left stage goes on the left, input feeding the right stage goes on the right. This prevents edges from crossing.

### Swimlane representation
Any stage with 2+ sub-steps → swimlane container with steps inside:
```xml
<mxCell id="sl-X" parent="1" vertex="1"
  style="swimlane;startSize=32;fillColor=#ffe6cc;strokeColor=#d79b00;fontStyle=1;fontSize=12;html=1;"
  value="Stage Name">
  <mxGeometry x="..." y="..." width="316" height="..." as="geometry" />
</mxCell>
```
Steps inside at x=18, width=280, with 30px gaps.

**CRITICAL: Every cell that uses `<br/>` in its value MUST include `html=1;` in the style.** Without it, `<br/>` renders as literal text instead of a line break.

**ALWAYS use `layout.py steps` to compute step positions inside swimlanes.** Never manually place steps — the minimum gap between steps is 30px and manual placement often makes them too close (resulting in tiny unreadable arrows between steps).

### Standalone boxes
Atomic stages (1 step) → rounded box:
```xml
<mxCell style="rounded=1;fillColor=#fff4e6;strokeColor=#d79b00;html=1;" .../>
```

## Coordinate Computation

Use `layout.py` for all coordinates:
```bash
python3 layout.py swimlanes <n>        # row of N parallel swimlanes
python3 layout.py inputs <n>           # input node row
python3 layout.py steps <sw_w> <startSize> <lines_per_step...>
python3 layout.py n-split <sw_w> <last_y> <last_h> <n_outcomes>
```

## Colour Palette

| Element | Fill | Stroke |
|---|---|---|
| Input node | `#dae8fc` | `#6c8ebf` |
| Swimlane header | `#ffe6cc` | `#d79b00` |
| Process step (inside swimlane) | `#ffffff` | same as parent swimlane stroke |
| Pass / output | `#d5e8d4` | `#82b366` |
| Fail | `#f8cecc` | `#b85450` |

**Step colouring rule**: Steps inside swimlanes MUST use white (`#ffffff`) fill with the swimlane's stroke colour as their border. This ensures steps pop from the swimlane body (`#fafafa`). Do NOT use the swimlane's fill colour for steps — they'll be invisible against the header.

## Labels

Use STANDARD detail level (3 lines max) on overview:
- Line 1: Step name
- Line 2: model name or key parameter
- Line 3: secondary parameter or file path

Use DETAILED (5 lines max) on drill-down pages.

**Richness principle**: every box should tell the reader something they couldn't guess from the title. Include model names, temperatures, file paths, output locations.

**Content-richness rules (MANDATORY):**
- Line 1: Step name (what it does, not just the filename)
- Line 2: Key detail (model name, threshold, or key parameter)
- Line 3: Secondary detail (output location, batch size, or protocol)
- **BAD**: "sweep.py / matrix driver" — tells reader nothing useful
- **GOOD**: "sweep.py / iterates model×arm×dataset / launches per-cell eval"
- **BAD**: "Validator" — could be anything
- **GOOD**: "LLM Scorer / rubric judge (minimax-m3) / mean≥8 gate"

If a box has only a filename with no explanation of what it does, the diagram has failed.

### Text-fit rule (MANDATORY)

Before writing any box, check that your text fits:
- **Max chars per line = (box_width - 16) / 5.5**
- 200px box → max 33 chars. 240px → max 40. 280px → max 48.
- Use `layout.py text-width "label<br/>detail"` to verify.
- If too long: abbreviate first, widen box second. NEVER leave overflowing text.

## Loop Annotations

For stages with iteration (for-loops, retries):
- Dashed border box around the repeated nodes
- Label at top-right: "per turn · repeated 3-7×"
- Style: `dashed=1;strokeColor=#999999;fillColor=none;opacity=60;`
- Use `layout.py loop-annotation` for coordinates

## XML Structure

After placing all nodes, compute page dimensions:
```bash
python3 ~/.kiro/skills/diagram/layout.py page-size <lowest_element_bottom_y> [rightmost_x]
```
Use the output `page_w` and `page_h` in the `<mxGraphModel>` tag. Never use default A4 dimensions.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="ac.draw.io">
  <diagram id="overview" name="Pipeline Overview">
    <mxGraphModel pageWidth="{from page-size}" pageHeight="{from page-size}" ...>
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- nodes with parent="1" -->
        <!-- steps inside swimlanes with parent="{swimlane_id}" -->
        <!-- edges with parent="1" for cross-row, parent="{swimlane_id}" for internal -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

## Edge Planning

After placing all nodes, create an edge plan JSON file and run `edge_planner.py`:
```bash
python3 edge_planner.py /tmp/edges.json
```

The input JSON must include all node positions and all edges:
```json
{
  "page_w": 827,
  "page_h": 1169,
  "nodes": {"node-id": {"x": 100, "y": 200, "w": 316, "h": 300}},
  "edges": [{"id": "e1", "source": "node-a", "target": "node-b", "label": "raw blocks", "protocol": "sequential"}]
}
```

The planner returns waypoints that route around all boxes. Use them in the XML:
```xml
<mxGeometry relative="1" as="geometry">
  <Array as="points">
    <mxPoint x="300" y="450" />
  </Array>
</mxGeometry>
```

For edges inside swimlanes (sequential steps), always use:
- exitX=0.5, exitY=1, entryX=0.5, entryY=0 (straight down, no waypoints needed)

## Swimlane Height Details

**CRITICAL: Always compute swimlane height from content. Never guess.**

```
Short title (≤ 40 chars):  startSize=32
Long title  (> 40 chars):  startSize=50, add whiteSpace=wrap
```

### Header startSize formula (MANDATORY)

Count the lines in your header value (`<br/>` splits):
```
startSize = 20 + (n_lines × 16)

1 line  (e.g. "Stage Name"):                    startSize = 36
2 lines (e.g. "Name<br/><font ...>subtitle"):   startSize = 52
```

**Why:** At fontSize=12 bold, each line needs ~16px. The 20px base covers top/bottom padding. If startSize is too small, the subtitle text overflows into the body or gets clipped.

For simple single-word headers ("Config", "Pipeline") you may use `startSize=32` as minimum — it's still comfortable. But if you add ANY subtitle line via `<br/>`, bump to at least 46.

Step height formula — count `<br/>` line breaks in the label:
```
n_lines = number of <br/> tags + 1
step_h  = max(36, 22 + n_lines × 18)
```

Swimlane total height — compute from actual content:
```
height = last_step_y + last_step_h + 20  (no split)
height = split_y + 36 + 20              (with pass/fail split)
```

**The height MUST equal the computed value — never round up by more than 10px.**
If you set height=900 but your last step ends at y=740, you have 160px of dead space. This looks wrong.

All swimlanes in the same row use `max(height)` so they align.

### Pass/fail split spacing

When a swimlane has a pass/fail split at the bottom:
- Leave at least 50px between the last step's bottom and the pass/fail boxes
- The pass/fail boxes need height=36 minimum
- Total: last_step_y + last_step_h + 50 (gap) + 36 (split) + 20 (padding) = swimlane height

### Sequential vs parallel stages

- **PARALLEL stages** (running at the same time): place SIDE-BY-SIDE in the same row
- **SEQUENTIAL stages** (one feeds the next): place STACKED VERTICALLY in separate rows

**Never place sequential stages side-by-side.** If stage A feeds stage B, they must be in separate rows with a vertical edge between them. Side-by-side implies they run in parallel.

### Minimum edge length between rows

Leave at least **60px vertical gap** between swimlanes/boxes in different rows. This gives edges room to show labels and arrowheads clearly. An edge shorter than 40px looks like floating text.

When computing swimlane y-positions: `next_row_y = previous_row_y + previous_row_height + 60`

This gap also keeps edge labels from overlapping with the boxes above/below.

## Edge Label Positioning

For cross-row edges (which use waypoints from the planner), position labels near the source:
- Add to the edge style: `labelPosition=left;align=right;`
- This pushes the label text toward the source end, away from the target where edges converge

For pass/fail edges: the label IS the pass/fail condition (e.g., "≥ 8", "< 8", "failed")

## Colour Legend

Add a legend BELOW all content on each page — never overlapping any box:
```xml
<mxCell id="legend" value="━━ sequential&lt;br/&gt;━━ &lt;font color=&quot;#82b366&quot;&gt;pass&lt;/font&gt;&lt;br/&gt;━━ &lt;font color=&quot;#b85450&quot;&gt;fail&lt;/font&gt;"
  style="text;html=1;align=left;verticalAlign=top;fontSize=10;fillColor=none;strokeColor=none;"
  vertex="1" parent="1">
  <mxGeometry x="20" y="{lowest_element_bottom + 40}" width="120" height="50" as="geometry" />
</mxCell>
```
**Position rule**: compute the y of the lowest element on the page (last output node, last swimlane bottom, etc.), then place the legend 40px below that. NEVER place it at a fixed y that might conflict with content.

## Pipeline Edge Limits

Pipelines have mostly vertical edges (straight down), so they tolerate more edges per page:
- **Overview**: up to 20 edges is fine (most go straight down between adjacent rows)
- **Drill-down**: up to 15 (one swimlane + a few inputs)
- Only flag as too dense if >25 edges on a single page
