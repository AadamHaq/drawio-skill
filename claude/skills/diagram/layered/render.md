# Layered Architecture Rendering Strategy

Use this for LAYERED topology repos — systems with horizontal bands of concern rather than sequential pipeline stages or distributed microservices.

**CRITICAL: Every mxCell that uses `<br/>` in its value MUST include `html=1;` in the style.** Without `html=1`, line breaks render as literal text.

## When to Use

- Config layer at the top, processing in the middle, environment/domain at the bottom
- Multiple independent tools/modules at the same level (not strictly sequential)
- Dispatcher or registry pattern that routes to tools based on config
- Components group by *concern* (all validators together) not by *execution order*

## Page Structure

Generate 1–2 pages:
1. **Architecture Overview** (portrait 827×1169) — all layers with items inside, edges between layers
2. **Tool Behavior Dispatch** (optional, portrait) — detail page showing how config drives tool selection

## Layout Approach

Use horizontal full-width bands stacked top-to-bottom. Items sit inside each band.

```bash
python3 ~/.kiro/skills/diagram/layout.py layers <n_layers> <items_per_layer...>
python3 ~/.kiro/skills/diagram/layout.py palette              # get colour pairs
python3 ~/.kiro/skills/diagram/layout.py boilerplate "Architecture Overview" "Tool Dispatch"
```

### Layer Band Style (the outer rectangle for each band)
```
rounded=1;whiteSpace=wrap;html=1;fillColor={from palette};strokeColor={from palette};
verticalAlign=top;fontStyle=1;fontSize=12;swimlane;startSize=30;
```

### Items Inside Layers
Items are rounded boxes centred inside their band:
```
rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor={layer_stroke};
verticalAlign=middle;fontSize=11;
```

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

**Environment containers** MUST have a background fill (`#fef5f5` — barely-there pink). Without it, the dashed border floats over white and doesn't register as a layer. Use `env_container` for the outer band and `submodule` (white + red border) for items inside.

## Coordinate Computation

```bash
# 3-layer architecture with 2 config items, 3 pipeline tools, 2 environment items
python3 ~/.kiro/skills/diagram/layout.py layers 3 2 3 2
```

Output gives you:
- `layer[i]: x y w h` — the full-width band rectangle
- `item[i,j]: x y w h` — positions relative to their layer band

Place items as children of their layer band (parent = layer cell id).

## Edge Rules

- Edges go **between layers** (top band → middle band, middle → bottom)
- Within a layer, items are peers — no edges between them unless there's a clear dependency
- Use `edge_planner.py` for cross-layer edges
- Edge labels: short (≤12 chars) — describe *what* flows, not *how*
- Max 12 edges on the overview page

### Edge styling
- Config → processor: solid `#6c8ebf` strokeWidth=2
- Processor → environment: solid `#82b366` strokeWidth=2
- Optional/conditional edges: `dashed=1;dashPattern=8 4;strokeColor=#d79b00;`

## Multi-Page Boilerplate

```bash
python3 ~/.kiro/skills/diagram/layout.py boilerplate "Pipeline Architecture" "Tool Behavior Dispatch"
```

Use the output as your starting XML skeleton, then fill in nodes and edges.

## Validation

After rendering, run:
```bash
python3 ~/.kiro/skills/diagram/validate.py architecture.drawio
```

Fix any issues before writing the final file. Key things to watch:
- Layer bands must be tall enough to contain their items (no overflow)
- Edges must not cross through layer bands they don't connect to
- Edge labels must not overlap items

## SVG Companion (optional)

For repos hosted on GitHub/GitLab where inline preview matters, also produce `architecture.svg`:
- SVGs render inline in READMEs; `.drawio` files don't
- Use the same layout/colours but as hand-authored SVG (not a draw.io export)
- Keep it simple: rectangles + text + lines with `marker-end` for arrows

## Example Structure

```
┌──────────────────── Config Layer ────────────────────┐
│  [prompts.yaml]    [eval_config.yaml]                │
└──────────────────────────────────────────────────────┘
          │                    │
          ▼                    ▼
┌──────────────────── Pipeline Layer ──────────────────┐
│  [Generator]    [Validator]    [Post-processor]      │
└──────────────────────────────────────────────────────┘
          │                    │
          ▼                    ▼
┌──────────────────── Environment Layer ───────────────┐
│  [LLM endpoint]         [Output storage]             │
└──────────────────────────────────────────────────────┘
```

Each `[box]` is an mxCell inside its parent layer band. Edges connect across layers.
