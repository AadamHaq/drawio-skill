# Service-Map Diagram Strategy

Use this strategy when the repo is classified as MICROSERVICE or HYBRID.

## Page Planning

Always generate at least 2 pages:
1. **Service Map** (landscape) — shows ALL services with containers. Show ONLY the most important edges (max 12). Omit redundant edges.
2. **Data Flow** (portrait) — pick the most interesting flow (e.g., voice pipeline) and show it in detail with fewer services and clear sequential flow.

Optional additional pages:
- One per conditional mode (if the system has cascade/openai/etc modes)
- Deployment view (infrastructure focus)

## Service Map Layout

### Layers (top to bottom)
```
Client      — browsers, mobile apps (yellow fill: #fff2cc)
Gateway     — API services, proxies (purple fill: #e1d5e7)
Service     — application services, realtime (purple fill: #e1d5e7)
Worker      — background processors, voice workers (purple fill: #e1d5e7)
Inference   — ML models, Triton, vLLM (purple fill: #e1d5e7)
Infrastructure — databases, caches, message brokers (blue cylinder: #dae8fc)
```

### Spacing
- Minimum 80px VERTICAL gap between layers
- Minimum 60px HORIZONTAL gap between services in the same layer
- Use the `service-map` layout calculator command for positions
- Use the page dimensions from the calculator (may be larger than 1169×827)

### Service Container Style
```
rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;
verticalAlign=top;fontStyle=1;fontSize=12;swimlane;startSize={see formula};
```
- Header: service name ONLY (bold, 12px)
- Internal components as child boxes: port, model name, features (11px)
- **startSize formula**: `20 + (n_lines × 16)`. Min 32 for 1-line, min 46 for 2-line headers.

### Infrastructure Style
```
shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;
boundedLbl=1;backgroundOutline=1;size=10;fontSize=12;
```
- Label: name + port only (e.g., "PostgreSQL :5432")

## Edge Selection for Service Map

**Critical: DO NOT show every possible edge.** Show only:
1. The PRIMARY flow path (client → gateway → services → workers)
2. Infrastructure connections (service → database, service → cache)
3. One representative edge per bidirectional pair

**Omit:**
- Duplicate edges (if RT-Text and RT-Voice both call LLM, show only ONE representative)
- Minor/internal edges that clutter the view
- Edges that would cross 3+ other services to reach their target

**Target: 8-12 edges on the service map page.** If you have more, remove the least important ones.

## Data Flow Page

- Portrait orientation (827×1169) — more vertical space for sequential flows
- Show only the services involved in ONE specific data path
- Use a swimlane container for the main processing service
- Internal steps as sequential boxes within the swimlane
- External services (STT, LLM, TTS, API) as standalone boxes connected to the swimlane

## Conditional Mode Groups

```
rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#d79b00;
strokeWidth=2;dashed=1;opacity=70;verticalAlign=top;fontStyle=2;fontSize=10;
```
- Dashed orange boundary around mode-specific services
- Label: "mode: cascade" or similar
- Use the `conditional-group` layout calculator command

## Topology Detection Signals

Classify as MICROSERVICE if 3+ of these are present:
- Docker-compose / Kubernetes manifests
- Multiple service directories with separate entrypoints
- Tiltfile or Helm charts
- Inter-service HTTP/gRPC clients in code
- WebSocket server/client patterns
- Always-running processes (web servers, workers)
