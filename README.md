# diagram-skill

A Claude and Kiro skill that analyses any repository and produces a
[draw.io](https://www.drawio.com) architecture diagram (`Claude.drawio.xml`).

## How it works

Run `/diagram` in any repo. The skill reads the codebase, computes all coordinates
using a small helper script (`layout.py`), and writes the XML in one shot. A
validation pass runs automatically before the file is written to catch overlapping
edges or edges routed through boxes.

`layout.py` requires only `python3` — no packages, no virtual environment.

`/diagram-validate` is available separately if you want to re-check an existing file.

## Capabilities

### Multi-Page Diagram Output

The skill produces a multi-page draw.io file with navigable tabs:

- **Overview page** — a high-level map of all stages using summary nodes (title + one-line description)
- **Drill-down pages** — detailed views of stages that have 3+ sub-steps or contain loops
- **NavLinks** — clickable links on overview nodes that navigate directly to the corresponding drill-down page

Simple repos (fewer than 3 stages, no drill-down threshold met) get a single enhanced overview page instead. The maximum is 8 drill-down pages; adjacent stages merge when that limit is exceeded.

### Rich Labels

Nodes display extracted values from the repository's config files and source code:

- **Detail levels**: OVERVIEW (max 2 lines), STANDARD (max 3 lines), DETAILED (max 5 lines)
- **Priority order**: model names → thresholds/temperatures → file paths
- **Truncation**: lines exceeding 40 characters are cut at 37 and suffixed with `...`
- **Security**: keys ending in `_KEY`, `_SECRET`, `_TOKEN`, `_PASSWORD`, `_CREDENTIAL` (and exact matches for `password`, `secret`, `token`, `api_key`) are automatically omitted
- **Paths**: always relative to the repo root — no `/Users/`, `/home/`, or `~` prefixes

### Loop / Cycle Annotations

Iteration patterns (for-loops, retries, per-item processing) are detected and annotated visually:

- A dashed-border box is drawn around repeated nodes with 15px padding and a 20px label area at the top
- Loop label format: `[loop context] · [bounds expression]` (e.g., "per turn · repeated 3–7×")
- Classification types: FIXED_COUNT, BOUNDED_RANGE, RETRY, PER_ITEM, UNTIL_CONDITION
- Graceful fallback when bounds are unknown (displays loop type without a specific count)

### N-Way Conditional Routing

Decision points support 2–10 outcomes (generalizing the previous binary pass/fail model):

- Exit points are distributed evenly along the decision node's bottom edge
- Each outcome edge gets its own routing band (10px apart) to prevent overlap
- Special case: 2 outcomes use exit positions at 0.25 and 0.75
- Each edge is labeled with its outcome condition

### New `layout.py` Commands

The coordinate calculator now supports additional commands:

```bash
# Nested container — positions children inside a parent swimlane container
python3 layout.py nested-container <parent_sw_w> <parent_start_y> <n_children> <lines_per_child...>

# Loop annotation — computes dashed-box coordinates around looped nodes
python3 layout.py loop-annotation <first_node_y> <last_node_y> <last_node_h> <sw_w>

# N-way split — computes outcome box positions for N-way decisions
python3 layout.py n-split <sw_w> <last_step_y> <last_step_h> <n_outcomes> [split_gap]

# Multi-page dimensions — returns page width, height, and orientation
python3 layout.py multipage <page_type> [n_swimlanes]
#   page_type: overview | drill_down | data_flow | service_map | deployment

# Service-map grid — computes layered grid positions for N services
python3 layout.py service-map <n_services> [layer_hints...]
#   layer_hints: client | gateway | service | worker | infrastructure

# Service container — computes internal component layout within a service box
python3 layout.py service-container <n_components> [container_w]

# Bidirectional edge — computes parallel offset exit/entry points for bidi edges
python3 layout.py bidirectional-edge <src_x> <src_y> <src_w> <src_h> <tgt_x> <tgt_y> <tgt_w> <tgt_h> [offset]

# Conditional group — computes dashed bounding box around mode-specific services
python3 layout.py conditional-group <x,y,w,h> <x,y,w,h> [...]
```

All commands print deterministic key=value output to stdout. Invalid arguments produce a usage message on stderr and exit non-zero.

### Multi-Page Validation

The validation pass (`/diagram-validate`) now handles multi-page files:

- Each page is checked independently for edge overlaps and edge-through-box crossings
- **NavLink consistency** — every link target must reference an existing page ID; the source must be a valid node on the containing page
- **Unique IDs** — node IDs are verified to be unique across all pages
- **Minimum approach distance** — edges with explicit waypoints must maintain ≥ 20px from the target vertex boundary
- Errors report page name, violation type, element IDs, and coordinates
- Validation failure prevents the diagram file from being written

### Microservice Topology Support

The skill automatically detects and renders service-oriented architectures:

- **Automatic topology classification** — detects pipeline vs microservice vs hybrid repos by scanning for docker-compose, k8s manifests, multiple service dirs, etc. Falls back to pipeline when confidence is low.
- **Service discovery** — scans docker-compose, k8s manifests, Helm charts, Tiltfiles, and service directories to extract names, ports, dependencies, and runtime types.
- **Communication edge mapping** — detects HTTP, gRPC, WebSocket, and pub/sub connections between services. Bidirectional pairs (A→B + B→A) collapse into a single bidi edge. Deduplicates by source/target/protocol.
- **Conditional mode groups** — dashed boundaries drawn around services active in specific configs (e.g., `cascade` vs `openai` mode), detected from env vars and config switches.
- **Layered service-map layout** — clients on top → gateways → services → workers → infrastructure. Within-layer swaps minimise edge crossings.
- **Protocol-coloured edges** — blue (HTTP), purple (gRPC), orange-dashed (WebSocket), green-dashed (pub/sub).
- **Bidirectional edges** — two parallel offset arrows for services that communicate both ways; rendered using computed perpendicular offsets.
- **Backward compatibility** — pipeline repos produce identical output; all existing commands and their outputs remain unchanged.

### Rich Mermaid Companion

The Mermaid markdown companion (`Claude.mermaid.md`) now includes:

- **Subgraph groupings** for related stages (`flowchart TD` with `subgraph` blocks)
- **Rich node labels** with config values: `NodeID["Title\ndetail1\ndetail2"]`
- **Loop annotations** via note blocks or back-edge syntax with bounds labels
- **Data shape section** — input/output schemas at stage boundaries as markdown tables or JSON code blocks
- All node IDs use valid Mermaid identifiers (alphanumeric + underscores only)

## Structure

```
diagram-skill/
├── claude/
│   ├── agents/
│   │   └── diagram.md          Agent definition (groups both skills)
│   └── skills/
│       ├── diagram/
│       │   ├── SKILL.md        Generate the diagram (multi-page, rich labels, loops, N-way routing)
│       │   └── layout.py       Coordinate calculator (swimlane, nested-container, loop-annotation, n-split, multipage, service-map, service-container, bidirectional-edge, conditional-group)
│       └── diagram-validate/
│           └── SKILL.md        Validate an existing diagram (per-page checks, NavLink consistency)
└── kiro/
    ├── agents/
    │   └── diagram.md
    └── skills/
        ├── diagram/
        │   ├── SKILL.md
        │   └── layout.py       (same as claude copy)
        └── diagram-validate/
            └── SKILL.md
```

## Installation

### Claude Code

Copy the skill and its helper script to `~/.claude/commands/`:

```bash
cp claude/skills/diagram/SKILL.md     ~/.claude/commands/diagram.md
cp claude/skills/diagram/layout.py    ~/.claude/commands/diagram_layout.py
cp claude/skills/diagram-validate/SKILL.md ~/.claude/commands/diagram-validate.md
```

Then invoke with `/diagram` or `/diagram-validate` in any Claude Code session.

### Kiro

Copy the skill and helper script into your project:

```bash
cp kiro/skills/diagram/SKILL.md     .kiro/steering/diagram.md
cp kiro/skills/diagram/layout.py    ~/.claude/commands/diagram_layout.py
cp kiro/skills/diagram-validate/SKILL.md .kiro/steering/diagram-validate.md
```

`layout.py` lives at `~/.claude/commands/diagram_layout.py` regardless of IDE — the
SKILL.md references it at that fixed path.

Kiro steering docs are always-active context, so the skill is available as soon as
you open the project.
