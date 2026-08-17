---
name: diagram
description: Analyse the current repository and write architecture.drawio — a draw.io architecture diagram with a Mermaid companion.
argument-hint: "[steering instructions]"
context: full
---

# Diagram Skill

Analyse the repository and produce `architecture.drawio` + `architecture.md`.

**Before starting, read these supporting files:**

#[[file:explore.md]]
#[[file:edge-rules.md]]
#[[file:validation-checklist.md]]

**Then read the appropriate strategy for the topology you detect:**
- For PIPELINE repos: #[[file:pipeline/render.md]]
- For MICROSERVICE repos: #[[file:microservice/render.md]]

## Workflow

### Step 1: Explore
Follow `explore.md`. Read the repo's entrypoints, configs, services. Classify as PIPELINE or MICROSERVICE.

### Step 2: Plan
- PIPELINE: decide which stages get drill-down pages (≥3 sub-steps or loops)
- MICROSERVICE: decide which services to show, which edges to include (max 12 per page), which data flow to detail on page 2

### Step 3: Compute Layout
The Python scripts (`layout.py`, `edge_planner.py`, `validate.py`) are in the same directory as this SKILL.md. Find them at `~/.kiro/skills/diagram/` and execute from there:
```bash
python3 ~/.kiro/skills/diagram/layout.py swimlanes <n>
python3 ~/.kiro/skills/diagram/layout.py inputs <n>
python3 ~/.kiro/skills/diagram/layout.py steps <sw_w> <startSize> <lines...>
python3 ~/.kiro/skills/diagram/layout.py service-map <n_services> <layer_hints...>
python3 ~/.kiro/skills/diagram/layout.py service-container <n_components>
python3 ~/.kiro/skills/diagram/layout.py multipage <page_type>
```

### Step 4: Plan Edges
For cross-row/cross-service edges, write a JSON file with all node positions and edges, then run:
```bash
python3 ~/.kiro/skills/diagram/edge_planner.py /tmp/edge_plan.json
```
The planner outputs waypoints that route around obstacles. Use the output exit/entry points AND waypoints in your XML:
```xml
<mxCell id="e1" edge="1" source="src" target="tgt"
  style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#6c8ebf;strokeWidth=2;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;"
  value="label">
  <mxGeometry relative="1" as="geometry">
    <Array as="points">
      <mxPoint x="300" y="450" />
      <mxPoint x="500" y="450" />
    </Array>
  </mxGeometry>
</mxCell>
```
If the planner returns empty waypoints `[]`, omit the `<Array as="points">` element.

For sequential edges WITHIN swimlanes (step→step): no planner needed, just use exitX=0.5 exitY=1 → entryX=0.5 entryY=0 with no waypoints.

### Step 5: Render XML
Follow `pipeline/render.md` or `microservice/render.md` depending on topology.

Key rules (from `edge-rules.md`):
- Every edge: `edgeStyle=orthogonalEdgeStyle;rounded=1;strokeWidth=2;`
- Use waypoints from `edge_planner.py` output for cross-service/cross-row edges
- Every cross-service edge gets a short label (5-15 chars)
- Protocol colours: HTTP=#6c8ebf, gRPC=#9673a6 (width 3), WebSocket=#d79b00 (dashed), pubsub=#82b366 (dashed)
- Add a colour legend box on each page (text cells listing protocol→colour)

### Step 6: Validate
Run `validation-checklist.md` — every item must pass. Then run:
```bash
python3 ~/.kiro/skills/diagram/validate.py architecture.drawio
```
Fix any issues reported before writing the final file.

### Step 7: Mermaid Companion
Write `architecture.md` with:
- Overview Mermaid flowchart (subgraph blocks, `<br/>` for multi-line labels)
- Drill-down diagrams per page
- Data Shapes table
- Config Snapshot table

## Steering
If `$ARGUMENTS` is provided, treat as free-form guidance (focus areas, filename, etc.)
