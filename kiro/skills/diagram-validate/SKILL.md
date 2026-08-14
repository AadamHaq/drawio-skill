---
name: diagram-validate
description: Read Claude.drawio.xml and check for overlapping edge segments, edges routed through boxes, NavLink consistency, and unique node IDs across all pages. Reports violations with coordinates.
argument-hint: "<xml-filename>"
context: full
agent: diagram
---

Read `Claude.drawio.xml` (or `$ARGUMENTS` if provided) and check it for routing
violations, structural consistency, and cross-page integrity. Report every
violation found with enough detail to fix it.

---

## Multi-page iteration

A multi-page drawio file contains one `<mxfile>` root with multiple `<diagram>`
child elements. Each `<diagram>` represents a page (tab).

**For every check below, iterate over each `<diagram>` element independently.**
Parse the `<mxGraphModel>` inside each diagram and collect its edges (`edge="1"`)
and vertices (`vertex="1"`) separately. Checks 1 and 2 are per-page; checks 3 and
4 are cross-page.

---

## What to check

### 1. Overlapping segments (per page)

Two edges running on top of each other — same horizontal segment (identical y,
overlapping x-range) or same vertical segment (identical x, overlapping y-range).

A crossing (two lines forming an X at a single point) is **not** a violation.

For each `<diagram>` element, collect all `mxCell` nodes with `edge="1"` within
that page's `<root>`:
- Reconstruct its path: start from `sourcePoint` or the source vertex's centre-bottom,
  through any `Array/mxPoint` waypoints, to `targetPoint` or the target vertex's centre-top.
- **Coordinate conversion**: child edges (parent = a swimlane or container id) have
  coordinates relative to their parent element. Convert to absolute page coordinates
  by adding the parent's x/y (and grandparent's x/y if nested deeper). Walk up the
  parent chain until you reach `parent="1"` (the page root).
- Break the path into horizontal and vertical segments.
- Compare every pair of segments from different edges **within the same page** for overlap.

### 2. Box-crossing (per page)

An edge segment passing through the interior of a vertex (not just touching its border).

For each `<diagram>` element independently, check each edge segment against all
vertices on that page:
- Horizontal segment at y: crosses box (bx, by, bw, bh) if `by < y < by+bh`
  AND the segment's x-range overlaps `(bx, bx+bw)` by more than a border touch.
- Vertical segment at x: crosses box if `bx < x < bx+bw`
  AND the segment's y-range overlaps `(by, by+bh)`.

Ignore the source and target vertices of that same edge (the segment is allowed to
start/end inside them).

### 3. NavLink validation (cross-page)

Every `link=page-{id}` style attribute in the entire mxfile must reference a target
page ID that exists as a `<diagram id="...">` element.

Steps:
1. Collect the set of all page IDs: for each `<diagram id="X">`, add `X` to the
   known page ID set.
2. For each `<diagram>`, scan all `mxCell` elements whose `style` attribute contains
   a `link=page-{id}` entry.
3. Verify the referenced `{id}` exists in the known page ID set.
4. Verify the source cell (the mxCell carrying the link) has `vertex="1"` and exists
   on the containing page (i.e., it is a valid node, not a floating reference).

A violation occurs if:
- The target page ID does not exist in the diagram's page set, OR
- The source cell is not a vertex on the page containing the link.

### 4. Unique node ID check (cross-page)

All `mxCell` `id` attributes must be unique across ALL pages in the mxfile — not
just within one page.

Steps:
1. Collect every `mxCell` `id` from every `<diagram>` element into a single list.
2. Check for duplicates. The reserved IDs `"0"` and `"1"` (root cells) are expected
   to repeat per page and are excluded from this check.
3. Any non-reserved `id` that appears more than once is a violation.

### 5. Minimum approach distance (per page)

When an edge uses explicit waypoints (one or more `<mxPoint>` elements in its
geometry), the last waypoint before the target must maintain at least **20 pixels**
of minimum approach distance from the target vertex boundary, measured along the
axis of entry.

For each edge with waypoints on a given page:
- Identify the last waypoint and the target vertex bounding box.
- Compute the perpendicular distance from the waypoint to the nearest face of the
  target vertex along the entry axis (horizontal or vertical depending on approach
  direction).
- If this distance is less than 20px, report a violation.

---

## Output format

If clean:
```
OK — no violations found. ({N} edges checked, {P} pages validated)
```

If violations found, list each one with the page name:
```
OVERLAP (horizontal)  page="Step 1: Generation"  y=1100  x=258–590  edge "e-mt-fail" ✕ edge "e-nlp-fail"
BOX-CROSSING  page="Pipeline Overview"  edge "e-cross"  segment (530,480)→(530,700)  through "Deduplication" [dedup_nlp]
NAVLINK-INVALID  page="Pipeline Overview"  cell "gen-summary"  link=page-nonexistent  (target page ID not found)
DUPLICATE-ID  id="step-gen-1"  found in pages: "Pipeline Overview", "Step 1: Generation"
APPROACH-DISTANCE  page="Step 2: Scoring"  edge "e-score-out"  waypoint (400,580)  distance=12px < 20px minimum
```

Then suggest the fix for each.

Validation failure SHALL prevent the diagram file from being written. If any
violation is reported, do not save the `.drawio` file — instead report the errors
and ask the user how to proceed.
