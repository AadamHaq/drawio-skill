---
name: diagram-validate
description: Read Claude.drawio.xml and check for overlapping edge segments or edges routed through boxes. Reports violations with coordinates.
argument-hint: "<xml-filename>"
context: full
agent: diagram
---

Read `Claude.drawio.xml` (or `$ARGUMENTS` if provided) and check it for the two
classes of routing violation. Report every one found with enough detail to fix it.

---

## What to check

### 1. Overlapping segments

Two edges running on top of each other — same horizontal segment (identical y,
overlapping x-range) or same vertical segment (identical x, overlapping y-range).

A crossing (two lines forming an X at a single point) is **not** a violation.

For each `mxCell` with `edge="1"`:
- Reconstruct its path: start from `sourcePoint` or the source vertex's centre-bottom,
  through any `Array/mxPoint` waypoints, to `targetPoint` or the target vertex's centre-top.
- Remember that child edges (parent = a swimlane id) have coordinates relative to the
  swimlane; convert to absolute by adding the swimlane's x/y.
- Break the path into horizontal and vertical segments.
- Compare every pair of segments from different edges for overlap.

### 2. Box-crossing

An edge segment passing through the interior of a vertex (not just touching its border).

For each segment, check whether it enters the bounding box of any vertex:
- Horizontal segment at y: crosses box (bx, by, bw, bh) if `by < y < by+bh`
  AND the segment's x-range overlaps `(bx, bx+bw)` by more than a border touch.
- Vertical segment at x: crosses box if `bx < x < bx+bw`
  AND the segment's y-range overlaps `(by, by+bh)`.

Ignore the source and target vertices of that same edge (the segment is allowed to
start/end inside them).

---

## Output format

If clean:
```
OK — no violations found. ({N} edges checked)
```

If violations found, list each one:
```
OVERLAP (horizontal)  y=1100  x=258–590  edge "e-mt-fail" ✕ edge "e-nlp-fail"
BOX-CROSSING  edge "e-cross"  segment (530,480)→(530,700)  through "Deduplication" [dedup_nlp]
```

Then suggest the fix for each.
