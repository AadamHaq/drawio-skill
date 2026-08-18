# Edge Rules (applies to ALL diagrams)

## Core Edge Style

Every edge MUST use this pattern:
```
edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor={color};strokeWidth={width};exitX={x};exitY={y};exitDx=0;exitDy=0;entryX={x};entryY={y};entryDx=0;entryDy=0;
```

- `edgeStyle=orthogonalEdgeStyle` — right-angle segments
- `rounded=1` — smooth corners
- For cross-service edges: use waypoints from `edge_planner.py` output (these route around boxes)
- For sequential edges inside swimlanes: no waypoints needed (straight down)
- Include `<Array as="points">` ONLY when the edge planner provides waypoints

**Exit/entry point rules:**
- Sequential (top→bottom): exitX=0.5 exitY=1 → entryX=0.5 entryY=0 (centre bottom → centre top)
- NEVER use 0.0 or 1.0 for the non-direction axis (e.g., exitX=0.0 looks like the arrow starts at the very pixel edge)
- Keep exit/entry values between 0.15 and 0.85 to stay visually inside the box border
- The arrow head direction is determined by the ENTRY point: entryY=0 means the arrow approaches from above (points down), entryX=0 means it approaches from the left (points right)

**Arrow head direction must match approach:**
- If the edge arrives at the TOP of a box → use entryY=0 (arrow points down into box)
- If the edge arrives at the BOTTOM → use entryY=1 (arrow points up into box)
- If the edge arrives from the LEFT → use entryX=0 (arrow points right into box)
- If the edge arrives from the RIGHT → use entryX=1 (arrow points left into box)

## Protocol Colours (service maps)

| Protocol | Color | Width | Extra |
|---|---|---|---|
| HTTP | `#6c8ebf` | 2 | solid |
| gRPC | `#9673a6` | 3 | solid |
| WebSocket | `#d79b00` | 2 | `dashed=1;dashPattern=12 4;` |
| pub/sub | `#82b366` | 2 | `dashed=1;dashPattern=8 4;` |
| database | `#6c8ebf` | 2 | `dashed=1;dashPattern=8 4;` |

## Pipeline Colours

| Meaning | Color |
|---|---|
| Pass/success | `#82b366` (green) |
| Fail/error | `#b85450` (red) |
| Neutral | default (no strokeColor override) |

## Labels

- Cross-service/cross-row edges: SHOULD have a label (5-12 chars max)
- Sequential edges within a swimlane: no label (value="")
- **HARD LIMIT: 12 characters maximum.** If the natural label is longer, abbreviate:
  - "ceval_to_responses.py" → "adapt" or "transform"
  - "uv run --frozen" → "run cell"
  - "raw/multi_turn.json" → "raw blocks"
- If you can't fit it in 12 chars, omit the label entirely (value="")
- The edge colour and context already communicates most meaning — labels are supplementary

## Exit/Entry Point Spreading

When multiple edges leave or enter the same node, spread them:
- 2 edges: use 0.3 and 0.7
- 3 edges: use 0.2, 0.5, 0.8
- 4 edges: use 0.15, 0.4, 0.6, 0.85
- NEVER stack edges at the same exit/entry point

## Bidirectional Edges

Two separate edges with offset exit/entry points:
- Forward: exitY=0.35, entryY=0.35 (upper path)
- Reverse: exitY=0.65, entryY=0.65 (lower path)
- Or for horizontal: exitX=0.35/0.65 similarly

## Maximum Edges Per Page

- If a page has more than 12-15 edges, it's too dense
- Split into multiple pages: one overview with major flows, separate data-flow pages for detail
