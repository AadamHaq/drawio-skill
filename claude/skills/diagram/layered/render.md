# Layered Architecture Rendering Strategy

Use this for LAYERED topology repos — systems with horizontal bands of concern rather than sequential pipeline stages or distributed microservices.

**CRITICAL: Every mxCell that uses `<br/>` in its value MUST include `html=1;` in the style.** Without `html=1`, line breaks render as literal text.

## When to Use

- Config layer at the top, processing in the middle, environment/domain at the bottom
- Multiple independent tools/modules at the same level (not strictly sequential)
- Dispatcher or registry pattern that routes to tools based on config
- Components group by *concern* (all validators together) not by *execution order*

## Page Structure

Generate 1–3 pages:
1. **Architecture Overview** — all layers with items inside, edges between layers. Use custom page dimensions (see `layout.py page-size`).
2. **Drill-down page** (one per module with ≥3 sub-steps) — shows internal flow with specific models, parameters per step. Same rules as pipeline drill-down pages: swimlane with sequential steps, external dependencies as standalone boxes.
3. **Tool Behavior Dispatch** (optional) — detail page showing how config drives tool selection

**Rule:** If any module in the middle layer has 3+ internal sub-steps (e.g., Generator with 5 steps), it MUST get its own drill-down page. The overview shows it as a single box; the drill-down page expands it.

## Layout Approach

Use horizontal full-width bands stacked top-to-bottom. Items sit inside each band visually.

```bash
python3 ~/.kiro/skills/diagram/layout.py layers <n_layers> <items_per_layer...>
python3 ~/.kiro/skills/diagram/layout.py palette              # get colour pairs
python3 ~/.kiro/skills/diagram/layout.py boilerplate "Architecture Overview" "Tool Dispatch"
```

### Layer Band Style (the outer rectangle for each band)
```
rounded=1;whiteSpace=wrap;html=1;fillColor={from palette};strokeColor={from palette};
verticalAlign=top;fontStyle=1;fontSize=12;swimlane;startSize={see formula};
```

### Header startSize formula (MANDATORY)

Count the lines in your header value (`<br/>` splits):
```
startSize = 20 + (n_lines × 16)

1 line  (e.g. "Pipeline"):                      startSize = 36
2 lines (e.g. "Name<br/><font ...>subtitle"):   startSize = 52
```

Minimum for single-word band names: `startSize=32`. If you add ANY subtitle line via `<br/>`, use at least 46.

### Items Inside Layers
Items are rounded boxes positioned inside their band area:
```
rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor={layer_stroke};
verticalAlign=middle;fontSize=11;
```

### Content-richness rules (MANDATORY)

Every item box MUST have at least 2 lines:
- Line 1: Component name / filename (bold via style)
- Line 2: What it DOES in specific terms (in `<font style="font-size:9px">`)

**BAD examples** (tell reader nothing):
- "sweep.py / matrix driver"
- "registry.py / resolve + load"
- "Validator"

**GOOD examples** (reader learns something):
- "sweep.py<br/><font style='font-size:9px'>iterates model×arm×dataset matrix, launches per-cell eval</font>"
- "registry.py<br/><font style='font-size:9px'>resolves environment by name → loads frozen ToolSpec+prompts+db-seed</font>"
- "LLM Scorer<br/><font style='font-size:9px'>rubric-driven judge (minimax-m3), mean≥8 pass gate</font>"

Include: model names, specific functions called, key thresholds, output formats. If a box only has a filename and a generic 2-word description, the diagram has failed.

### Text-fit rule (MANDATORY)

Before writing any box, check that your text fits:
- **Max chars per line = (box_width - 16) / 5.5**
- 200px box → max 33 chars per line
- 240px box → max 40 chars per line
- 280px box → max 48 chars per line

Use `layout.py text-width "your label<br/>second line"` to verify. If the text is too long:
1. First try abbreviating (remove filler words, use shorter model names)
2. If still too long, widen the box (and adjust sibling positions)
3. NEVER leave text that overflows — it clips in both draw.io and SVG

## Colour Palette (by layer role)

Use `layout.py palette` for exact values. Typical mapping:

| Layer role | Fill | Stroke | Palette key |
|---|---|---|---|
| Config / input | `#dae8fc` | `#6c8ebf` | `config` |
| Generator / process | `#fff2cc` | `#d6b656` | `generator` |
| Validator | `#d5e8d4` | `#82b366` | `validator` |
| Post-processing | `#e1d5e7` | `#9673a6` | `postprocess` |
| Environment container (dashed) | `#fef5f5` | `#b85450` | `env_container` |
| Environment item (solid) | `#f8cecc` | `#b85450` | `environment` |
| Sub-module (inside env) | `#ffffff` | `#b85450` | `submodule` |

### Band header fill contrast

Band headers MUST have a visibly opaque fill — NOT near-white values like `#f9f9f9` or `#fafafa`. Use at least `#f0f0f0` for neutral bands. This ensures edge lines are visually masked when they pass behind the header in z-order.

Coloured bands (Generator=#fff2cc, Validator=#d5e8d4) already have sufficient contrast.

**Environment containers** MUST have a visible background fill (`#fef5f5` — barely-there pink). Without it, the dashed border floats over white and doesn't register as a layer.

## Coordinate Computation

```bash
python3 ~/.kiro/skills/diagram/layout.py layers 3 1 3 3
```

Output gives you:
- `layer[i]: x y w h` — the full-width band rectangle
- `item[i,j]: x y w h` — positions relative to their layer band

### Arrow clearance below band headers (CRITICAL)

When edges arrive at items from a layer above, items MUST be positioned with enough gap below the band header for arrowheads to be fully visible:

```
item_y_absolute = band_y + startSize + 24px (minimum)
```

24px clearance = 10px arrowhead + 16px breathing room.

**HARD RULE: first child y = startSize + 26. The `layout.py steps` command enforces this automatically (it outputs first_step_y = startSize + 26). NEVER place a child closer to the header.**

**HARD RULE: last child bottom must be ≥15px above parent bottom.** Set parent height = last_child_y + last_child_h + 15. Children must NEVER overflow below or touch the parent border.

**Example:** Band at y=150 with startSize=32 → header bottom at y=182 → items start at y=208 minimum (150+32+26=208).

If you violate this, arrowheads will be clipped by the header rendering on top, or arrows will appear to start/end in mid-air behind the header. This looks broken in both draw.io proper AND the SVG renderer.

### Items as root-level siblings (REQUIRED when edges arrive from above)

For items that receive edges from a layer above, place them as **root-level siblings** (`parent="1"`) positioned visually inside the band area. Do NOT make them children of the band. This avoids:
- Parent offset confusion in entry point calculation
- Arrowheads hidden behind parent band headers (z-order issue)
- Validator false positives about edges "crossing" the parent band
- Edges appearing to enter "through" the band header

The band becomes a pure visual background rectangle. Items use absolute coordinates.

```xml
<!-- Band is visual background only — no children with incoming edges -->
<mxCell id="L1" value="Pipeline" style="swimlane;startSize=32;fillColor=#f0f0f0;..." parent="1">
  <mxGeometry x="30" y="150" width="767" height="320" />
</mxCell>

<!-- Items are root-level siblings, positioned inside L1's visual area -->
<mxCell id="gen" value="Generator" style="swimlane;startSize=22;fillColor=#fff2cc;..." parent="1">
  <mxGeometry x="48" y="204" width="210" height="250" />  <!-- y = 150+28+26 = 204 -->
</mxCell>
<mxCell id="val" value="Validator" style="swimlane;startSize=22;fillColor=#d5e8d4;..." parent="1">
  <mxGeometry x="308" y="204" width="210" height="250" />
</mxCell>
```

Items that DON'T receive edges from outside (sub-steps inside modules, env tool specs) can remain as children of their container.

### Horizontal gap between sibling items

Items side-by-side in the same layer need **at least 50px horizontal gap**. This ensures:
- Horizontal data-flow edges between them are visible
- Edge labels have room (or can be omitted cleanly)

For a 767px-wide band with 3 items of width 210: gap = (767 - 3×210 - 2×18) / 2 ≈ 50px.

If your labels are short (≤6 chars), 50px is fine. If labels are longer, widen gaps to 80px+ (shrink items accordingly).

### Vertical gap between layers

Leave at least **50px vertical gap** between band bottoms and the next band top:

```
Config band:     y=30,  h=70   → bottom at y=100
                 50px gap
Pipeline band:   y=150, h=320  → bottom at y=470
                 75px gap (dashed env-call labels sit here)
Environment:     y=545, h=105  → bottom at y=650
```

The gap between Pipeline and Environment should be **75px minimum** because dashed edges + their labels traverse this gap. 75px gives: 15px below pipeline + 45px label space + 15px above environment.

## Edge Rules

### Config → Pipeline edges

**Option A (simplest): Single band-to-band arrow.**
Draw ONE edge from config band to pipeline band. Implies all children receive config. No header-crossing risk.

**Option B: Config item to individual modules.**
If you want separate arrows per module:
1. Source from the config ITEM (white box), not the config band
2. Use `exitX` spread (0.25, 0.5, 0.75) to fan out
3. Route through the GAP between bands (the 50px space between config bottom and pipeline top)
4. Horizontal jog at gap midpoint to align with target module center
5. Then straight down into the module top

```xml
<!-- Left arrow: exit bottom-left, horizontal jog in gap at y=140, down to gen -->
<mxCell id="e-cfg-gen" edge="1" source="cfg" target="gen"
  style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#6c8ebf;strokeWidth=2;
         exitX=0.25;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;">
  <mxGeometry relative="1" as="geometry">
    <Array as="points">
      <mxPoint x="318" y="140" />
      <mxPoint x="153" y="140" />
    </Array>
  </mxGeometry>
</mxCell>

<!-- Middle arrow: even when aligned, MUST have a waypoint in the gap -->
<mxCell id="e-cfg-val" edge="1" source="cfg" target="val"
  style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#6c8ebf;strokeWidth=2;
         exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;">
  <mxGeometry relative="1" as="geometry">
    <Array as="points">
      <mxPoint x="413" y="130" />
    </Array>
  </mxGeometry>
</mxCell>
```

**CRITICAL: ALL cross-band edges MUST include TWO waypoints:**
1. One in the **gap** between bands: `y = source_band_bottom + (target_band_top - source_band_bottom) / 3`
2. One **below the target band's header**: `y = target_band_y + startSize + 5`

This ensures the edge enters the target band below its header text — never crossing through it.

```xml
<!-- Example: edge from L1 item to L2 item -->
<!-- L1 bottom = 328, L2 top = 378, L2 header bottom = 406 -->
<Array as="points">
  <mxPoint x="168" y="345" />  <!-- gap waypoint -->
  <mxPoint x="420" y="410" />  <!-- below L2 header -->
</Array>
```

**NEVER** draw an edge that passes through a band header with visible text. The arrow will appear clipped or crossing through the title.

### Horizontal data-flow edges (sibling-to-sibling)

For edges between adjacent modules in the same layer (gen→val, val→post):

- Style: `exitX=1;exitY=0.5` → `entryX=0;entryY=0.5` (center of side faces)
- **Gap < 80px → NO LABEL on the edge.** Set `value=""`. Place a text annotation cell above the gap instead:

```xml
<!-- Edge with no label (gap too narrow) -->
<mxCell id="e-gen-val" edge="1" source="gen" target="val" value=""
  style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#82b366;strokeWidth=2;
         exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;" />

<!-- Separate text annotation above the gap -->
<mxCell id="lbl-gen-val" value="raw blocks"
  style="text;html=1;fontSize=8;fillColor=none;strokeColor=none;fontColor=#82b366;fontStyle=2;"
  vertex="1" parent="1">
  <mxGeometry x="255" y="310" width="60" height="14" />
</mxCell>
```

- **Gap ≥ 80px → label is fine** on the edge itself (value="raw blocks").

### Vertical/dashed edges to Environment layer

For edges going from pipeline modules down to the environment band:

1. **Label placement: ALWAYS to the side, never centered on the line.**
   Add `labelPosition=right;align=left;` to the edge style:

```xml
<mxCell id="e-gen-env" edge="1" source="gen" target="env" value="execute_tool()"
  style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#b85450;strokeWidth=2;
         dashed=1;dashPattern=8 4;labelPosition=right;align=left;
         exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.2;entryY=0;entryDx=0;entryDy=0;">
```

   This places the label text to the right of the edge in draw.io proper. For renderers that don't support `labelPosition`, use a waypoint trick:

2. **Waypoint trick for label positioning:**
   Add a short horizontal jog in the gap between layers. The label attaches to this horizontal segment (which has room):

```xml
<Array as="points">
  <mxPoint x="153" y="510" />  <!-- down to gap midpoint -->
  <mxPoint x="183" y="510" />  <!-- short 30px horizontal jog -->
</Array>
```

   The label sits on the horizontal segment, offset from the vertical portion of the line.

3. **Label proximity to boxes above:**
   The waypoint y should be at least **30px below** the module bottom. If the module bottom is at y=454 (204+250), place the waypoint at y=490+ so the label doesn't crowd the module.

### Edge styling summary

| Edge type | Color | Style | Label rule |
|---|---|---|---|
| Config → pipeline | `#6c8ebf` | solid, strokeWidth=2 | no label |
| Data flow (sibling→sibling) | `#82b366` | solid, strokeWidth=2 | only if gap ≥ 80px; else text annotation |
| Module → environment | `#b85450` | dashed (8 4), strokeWidth=2 | labelPosition=right OR waypoint trick |
| Optional/conditional | `#d79b00` | dashed (8 4), strokeWidth=2 | short label, same rules |

## Validation

After rendering, run:
```bash
python3 ~/.kiro/skills/diagram/validate.py architecture.drawio
```

**Expected false positives for layered diagrams:** The validator will flag edges as "crossing" the Pipeline band (L1) because L1 is a full-width background and all edges pass through its area. This is correct by design when using root-level siblings. Suppress these for background bands.

Fix any OTHER issues. Key checks:
- Layer bands tall enough to contain their items
- Edge labels not overlapping items
- Arrowheads not clipped by headers (24px clearance rule)
- No label on edges crossing gaps < 80px

## SVG Export

```bash
python3 ~/.kiro/skills/diagram/render_svg.py architecture.drawio architecture.svg
```

If the SVG has artefacts, the fix is almost always in the **drawio XML** (better waypoints, wider gaps, labelPosition style), not in the renderer. The renderer faithfully reproduces what the drawio says.

## Example Structure

```
┌──────────────────── Config Layer ────────────────────┐
│  [generation_plan_*.yaml]                            │
└──────────────────────────────────────────────────────┘
     │              │              │
     ▼              ▼              ▼         ← arrows clear of header (24px gap)
┌──────────────────── Pipeline Layer ──────────────────┐
│                                                      │
│  ┌─────────┐  ──→  ┌──────────┐  ──→  ┌──────────┐│
│  │Generator│       │ Validator │       │Post-Proc  ││
│  └─────────┘       └──────────┘       └──────────┘│
│                                                      │
└──────────────────────────────────────────────────────┘
     ┊                     ┊
     ┊ execute_tool()      ┊ validate()    ← labels to the RIGHT of dashes
     ▼                     ▼
┌╌╌╌╌╌╌╌╌╌╌╌╌ Environment Layer ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┐
┊  [tool_1]         [tool_2]         [tool_3]          ┊
└╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┘
```
