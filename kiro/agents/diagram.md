---
name: diagram
description: Analyse a repository and produce a draw.io architecture diagram. Use the diagram skill to generate, then diagram-validate to check the output.
skills:
  - diagram
  - diagram-validate
inclusionMode: manual
---

# Diagram Agent

Turns any repository into a clean draw.io architecture diagram by writing a simple
spec file and letting `generate.py` handle all coordinate maths.

## Workflow

1. Invoke `diagram` skill — explores the repo, writes `diagram-spec.yaml`, runs
   `generate.py` to produce `Claude.drawio.xml`.
2. Invoke `diagram-validate` skill — checks the XML for overlapping edges or edges
   routed through boxes, and reports any violations.
3. Open `Claude.drawio.xml` in draw.io or diagrams.net to export as PNG/SVG.

## What makes a good diagram

- Inputs at the top, outputs at the bottom
- Parallel stages side-by-side as swimlanes; sequential stages stacked vertically
- Edges cross freely but never overlap or pass through labelled boxes
- Decision branches are labelled (pass/fail, valid/invalid); sequential steps are not
