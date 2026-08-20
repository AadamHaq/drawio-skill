# Microservice Rendering Strategy

Use this for MICROSERVICE or HYBRID topology repos.

**CRITICAL: Every mxCell that uses `<br/>` in its value MUST include `html=1;` in the style.** Without `html=1`, line breaks render as literal text.

## Page Structure

Always generate at least 2 pages:
1. **Service Map** (landscape) — all services with containers, max 12 edges
2. **Data Flow** (portrait) — one focused flow (e.g., voice pipeline, request lifecycle)

Optional:
- Additional data-flow pages per conditional mode
- Deployment view

## Service Map Layout

### Layers (top to bottom, 80px+ gaps between layers)
| Layer | Examples | Fill colour |
|---|---|---|
| Client | Web browser, mobile app | `#fff2cc` (yellow) |
| Gateway | API gateway, reverse proxy | `#e1d5e7` (purple) |
| Service | Application services, realtime | `#e1d5e7` (purple) |
| Worker | Background processors, voice workers | `#e1d5e7` (purple) |
| Inference | ML models (LLM, STT, TTS, guards) | `#e1d5e7` (purple) |
| Infrastructure | Databases, caches, message brokers | `#dae8fc` (blue cylinder) |

### Service container style
```
rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;
verticalAlign=top;fontStyle=1;fontSize=12;swimlane;startSize=30;
```
- Header: service name ONLY (bold, 12px)
- First child box: port/model (e.g., "FastAPI :8000")
- Subsequent child boxes: features/components (11px)

**Content-richness rules (MANDATORY):**
- Every service container must have at least 2 child boxes (port + primary feature)
- Child boxes should name specific tech, not generic descriptions
- **BAD**: "API" with child "Server" — tells reader nothing
- **GOOD**: "API" with children "FastAPI :8000", "Auth / Sessions", "Banking (BoA)"
- **BAD**: "LLM" with child "model"
- **GOOD**: "LLM" with children "vLLM (OpenAI API)", "LMCache"
- Include model names, frameworks, ports for every service

### Text-fit rule (MANDATORY)

Service containers are 200px wide. Child box labels must fit:
- Max ~33 chars per child box line (at 200px width)
- Header sub-title (in `<font>` tag): max 38 chars (header is full container width)
- Use `layout.py text-width "label"` to verify before writing XML
- If a service has a long name+description, widen the container to 240px

### Infrastructure style
```
shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;
boundedLbl=1;backgroundOutline=1;size=10;fontSize=12;
```

### Coordinate computation
```bash
python3 layout.py service-map <n_services> <layer_hints...>
python3 layout.py service-container <n_components> [container_w]
python3 layout.py multipage service_map
```

## CRITICAL: Edge Density Management

The #1 failure mode for service maps is too many edges. Rules:

1. **Maximum 12 edges on the service map page.** Count them. If >12, remove the least important.
2. **Choose which edges to show:**
   - Primary request path (client → gateway → service → worker) — ALWAYS show
   - Infrastructure connections (→ database, → cache) — show
   - One edge per service pair, even if multiple protocols exist — pick the primary one
3. **Do NOT show:**
   - Both directions of a bidirectional pair (show only the "forward" direction with a note)
   - Redundant edges (if 2 services both call LLM, show only one representative edge)
   - Monitoring/observability connections
4. **Run `edge_planner.py`** after placing all nodes to get optimized exit/entry points

## Data Flow Page

- Portrait — use custom page dimensions from `layout.py page-size`
- Show ONE processing path through the system
- Main processor as a swimlane with sequential internal steps
- External dependencies as standalone boxes around the swimlane
- Few edges (5-8 max)
- Sequential internal edges: exitX=0.5 exitY=1 → entryX=0.5 entryY=0
- **Swimlane height MUST match content** — compute from last step position + 20px padding. Never leave 100+ px of empty space at the bottom.

**CRITICAL: ALWAYS compute step positions with `layout.py steps`:**
```bash
python3 ~/.kiro/skills/diagram/layout.py steps <swimlane_w> <startSize> <lines_per_step...>
```
Copy the output y-positions directly into your mxCell geometries. NEVER manually compute step y-positions — this causes overlapping steps that make the page unreadable.

## Conditional Mode Groups

Dashed boundary around services active only in certain configs:
```
rounded=1;fillColor=none;strokeColor=#d79b00;strokeWidth=2;dashed=1;opacity=70;
verticalAlign=top;fontStyle=2;fontSize=10;
```
Use `layout.py conditional-group <positions...>` for coordinates.

## Protocol Edge Styles

| Protocol | Style string |
|---|---|
| HTTP | `edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#6c8ebf;strokeWidth=2;` |
| gRPC | `edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#9673a6;strokeWidth=3;` |
| WebSocket | `edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#d79b00;strokeWidth=2;dashed=1;dashPattern=12 4;` |
| pub/sub | `edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#82b366;strokeWidth=2;dashed=1;dashPattern=8 4;` |
| database | `edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#6c8ebf;strokeWidth=2;dashed=1;dashPattern=8 4;` |

**NEVER add manual waypoints that you calculated yourself. Only use waypoints from `edge_planner.py`.** The planner computes obstacle-avoiding paths. Run it with a JSON file listing all node positions and edges, then use the returned waypoints in your XML.

## Edge Labels

Every cross-service edge MUST have a short label (5-15 chars):
"REST /api", "gRPC audio", "WebSocket", "queries", "sessions", "completions"

**Duplicate label rule:** If two edges would carry the same label (e.g., both labeled "completions" because RT-Text and RT-Voice both call LLM), differentiate them: "text comp" and "voice comp". The reader must know which arrow is which without tracing the line.

**Page dimensions:** After placing all nodes, compute custom page size:
```bash
python3 ~/.kiro/skills/diagram/layout.py page-size <lowest_element_bottom_y> [rightmost_x]
```
Use the output in `<mxGraphModel pageWidth="..." pageHeight="...">`. Never default to 1169×827.

## XML Structure

```xml
<diagram id="service-map" name="Service Map">
  <mxGraphModel pageWidth="{from layout.py}" pageHeight="{from layout.py}" ...>
    <root>
      <mxCell id="0" />
      <mxCell id="1" parent="0" />
      <!-- Service containers: parent="1" -->
      <!-- Components inside containers: parent="{container_id}" -->
      <!-- All edges: parent="1", NO manual waypoints -->
    </root>
  </mxGraphModel>
</diagram>
```

## Edge Label Positioning

Labels appear at the midpoint of the edge path by default. To avoid overlap:
- Add to the edge style: `labelPosition=left;align=right;` — pushes label toward source
- Keep labels under 12 chars for service maps (space is tight)
- If two edge labels would overlap, shorten one or remove the less important one

## Colour Legend

Add a legend that does NOT overlap any service box. Position it BELOW all content:
```xml
<mxCell id="legend" value="━━ &lt;font color=&quot;#6c8ebf&quot;&gt;HTTP&lt;/font&gt;&lt;br/&gt;━━━ &lt;font color=&quot;#9673a6&quot;&gt;gRPC&lt;/font&gt;&lt;br/&gt;┄┄ &lt;font color=&quot;#d79b00&quot;&gt;WebSocket&lt;/font&gt;&lt;br/&gt;┄┄ &lt;font color=&quot;#82b366&quot;&gt;pub/sub&lt;/font&gt;"
  style="text;html=1;align=left;verticalAlign=top;fontSize=10;fillColor=none;strokeColor=none;"
  vertex="1" parent="1">
  <mxGeometry x="20" y="{lowest_element_bottom + 40}" width="130" height="70" as="geometry" />
</mxCell>
```
**Position rule**: find the y of the lowest element on the page + its height + 40px margin. Place the legend there. NEVER use a fixed y value that might land on top of a service container.
